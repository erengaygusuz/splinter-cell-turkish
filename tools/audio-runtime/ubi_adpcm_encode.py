#!/usr/bin/env python3

import argparse
import copy
import struct
import wave
from dataclasses import dataclass
from pathlib import Path


ADPCM4_TABLE1 = [
    -100000000, 8, 269, 425, 545, 645, 745, 850,
]

ADPCM4_TABLE2 = [
    -1536, 2314, 5243, 8192, 14336, 25354, 45445, 143626,
]

DELTA_TABLE = [
    1024, 1031, 1053, 1076, 1099, 1123, 1148, 1172,
    1198, 1224, 1251, 1278, 1306, 1334, 1363, 1393,
    1423, 1454, 1485, 1518, 1551, 1584, 1619, 1654,
    1690, 1726, 1764, 1802, 1841, 1881, 1922, 1964,
    2007,
    -1024, -1031, -1053, -1076, -1099, -1123, -1148, -1172,
    -1198, -1224, -1251, -1278, -1306, -1334, -1363, -1393,
    -1423, -1454, -1485, -1518, -1551, -1584, -1619, -1654,
    -1690, -1726, -1764, -1802, -1841, -1881, -1922, -1964,
    -2007,
]


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def clamp16(v):
    return clamp(v, -32768, 32767)


def i16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def sign(v):
    return -1 if v < 0 else 1


def absmax16(v, limit):
    if v < -limit:
        return -limit
    if v > limit:
        return limit
    return v


@dataclass
class State:
    signature: int = 2

    step1: int = 1280
    next1: int = 0
    next2: int = 0

    coef1: int = 0
    coef2: int = 0

    mod1: int = 0
    mod2: int = 0
    mod3: int = 0
    mod4: int = 0

    hist1: int = 0
    hist2: int = 0

    delta1: int = 0
    delta2: int = 0
    delta3: int = 0
    delta4: int = 0
    delta5: int = 0


def expand_code_4bit(code, s):
    code_signed = code - 7
    step_index = abs(code_signed)

    if step_index > 7:
        raise ValueError(f"invalid Ubisoft 4-bit code: {code}")

    step_next = ADPCM4_TABLE1[step_index] + s.step1

    step = (s.step1 & 0xFFFF) * 246
    step = (step + ADPCM4_TABLE2[step_index]) >> 8
    step = clamp(step, 271, 2560)

    delta0 = 0

    # Equivalent to the decoder's bit-test for the normal valid range.
    if step_next >= 256:
        delta_index = ((step_next >> 3) & 0x1F)
        if code_signed < 0:
            delta_index += 33

        delta_shift = clamp((step_next >> 8) & 0xFF, 0, 31)

        delta0 = (
            DELTA_TABLE[delta_index] << delta_shift
        ) >> 10

    next0 = i16(
        (
            s.mod1 * s.delta1
            + s.mod2 * s.delta2
            + s.mod3 * s.delta3
            + s.mod4 * s.delta4
        ) >> 10
    )

    predicted = (
        s.coef1 * s.hist1
        + s.coef2 * s.hist2
    ) >> 10

    sample = i16(delta0 + next0 + predicted)

    coef1_next = s.coef1 * 255
    coef2_next = s.coef2 * 254

    delta0 = i16(delta0)

    if delta0 + next0 != 0:
        sign1 = sign(delta0 + next0) * sign(s.delta1 + s.next1)
        sign2 = sign(delta0 + next0) * sign(s.delta2 + s.next2)

        coef_delta = i16(
            (
                ((sign1 * 3072 + coef1_next) >> 6)
                & ~0x3
            )
        )

        coef_delta = clamp16(
            clamp16(coef_delta + 30719)
            - 30719
        )

        coef_delta = clamp16(
            clamp16(coef_delta - 30720)
            + 30720
        )

        coef_delta = (
            i16(sign2 * 1024)
            - i16(sign1 * coef_delta)
        ) * 2

        coef1_next += sign1 * 3072
        coef2_next += coef_delta

    s.hist2 = s.hist1
    s.hist1 = sample

    s.coef2 = absmax16(
        i16(coef2_next >> 8),
        768,
    )

    s.coef1 = absmax16(
        i16(coef1_next >> 8),
        960 - s.coef2,
    )

    s.next2 = s.next1
    s.next1 = next0
    s.step1 = step

    s.delta5 = s.delta4
    s.delta4 = s.delta3
    s.delta3 = s.delta2
    s.delta2 = s.delta1
    s.delta1 = delta0

    s.mod4 = clamp16(
        s.mod4 * 255
        + 2048 * sign(s.delta1) * sign(s.delta5)
    ) >> 8

    s.mod3 = clamp16(
        s.mod3 * 255
        + 2048 * sign(s.delta1) * sign(s.delta4)
    ) >> 8

    s.mod2 = clamp16(
        s.mod2 * 255
        + 2048 * sign(s.delta1) * sign(s.delta3)
    ) >> 8

    s.mod1 = clamp16(
        s.mod1 * 255
        + 2048 * sign(s.delta1) * sign(s.delta2)
    ) >> 8

    return sample


def choose_code(target, state):
    best = None

    # Code 15 maps to magnitude 8 and the decoder itself flags it
    # as outside the normal valid encoder range.
    for code in range(15):
        candidate_state = copy.copy(state)
        decoded = expand_code_4bit(
            code,
            candidate_state,
        )

        error = abs(int(target) - int(decoded))

        rank = (
            error,
            abs(code - 7),
            code,
        )

        if best is None or rank < best[0]:
            best = (
                rank,
                code,
                decoded,
                candidate_state,
            )

    _, code, decoded, new_state = best

    state.__dict__.update(
        new_state.__dict__
    )

    return code, decoded


def pack_state(s):
    return struct.pack(
        "<Iiii18h",
        s.signature,
        s.step1,
        s.next1,
        s.next2,

        s.coef1,
        s.coef2,
        0,
        0,

        s.mod1,
        s.mod2,
        s.mod3,
        s.mod4,

        s.hist1,
        s.hist2,
        0,
        0,

        s.delta1,
        s.delta2,
        s.delta3,
        s.delta4,

        s.delta5,
        0,
    )


def pack_codes_4bit(codes):
    out = bytearray()

    full = len(codes) // 8

    # Normal complete groups:
    #
    # 8 x 4-bit codes -> uint32 LE
    #
    # The decoder loads the uint32 as LE and then consumes
    # codes from the most-significant nibble downwards.
    for group_index in range(full):
        group = codes[
            group_index * 8:
            group_index * 8 + 8
        ]

        value = 0

        for i, code in enumerate(group):
            value |= (
                (code & 0x0F)
                << (28 - i * 4)
            )

        out += struct.pack("<I", value)

    rem = codes[full * 8:]

    # Ubisoft short final subframes are not necessarily
    # 32-bit aligned. Store the remaining nibbles without
    # attempting a negative bit shift.
    #
    # For even remainder:
    #   2 codes -> 1 data byte + padding byte
    #
    # For odd remainder:
    #   final code occupies the high nibble of the last byte;
    #   low nibble is unused/padding.
    i = 0

    while i + 1 < len(rem):
        out.append(
            ((rem[i] & 0x0F) << 4)
            | (rem[i + 1] & 0x0F)
        )
        i += 2

    if i < len(rem):
        out.append(
            (rem[i] & 0x0F) << 4
        )
    else:
        # Format adds one padding byte when code data
        # itself ends on a byte boundary.
        out.append(0)

    return bytes(out)


def read_pcm(path):
    with wave.open(str(path), "rb") as w:
        if w.getnchannels() != 1:
            raise ValueError("WAV must be mono")

        if w.getsampwidth() != 2:
            raise ValueError("WAV must be signed 16-bit PCM")

        if w.getframerate() != 36000:
            raise ValueError("WAV must be 36000 Hz")

        frames = w.readframes(
            w.getnframes()
        )

        samples = list(
            struct.unpack(
                f"<{len(frames) // 2}h",
                frames,
            )
        )

    return samples


def encode(samples, template):
    sample_count = len(samples)

    codes_per_subframe = 1536

    subframe_count = (
        sample_count
        + codes_per_subframe
        - 1
    ) // codes_per_subframe

    last_count = (
        sample_count
        - (
            subframe_count - 1
        ) * codes_per_subframe
    )

    header = bytearray(
        template[:0x30]
    )

    if len(header) != 0x30:
        raise ValueError(
            "template has no complete 0x30 header"
        )

    struct.pack_into("<I", header, 0x00, 8)
    struct.pack_into(
        "<I", header, 0x04,
        sample_count,
    )
    struct.pack_into(
        "<I", header, 0x08,
        subframe_count,
    )
    struct.pack_into(
        "<I", header, 0x0C,
        last_count,
    )
    struct.pack_into(
        "<I", header, 0x10,
        codes_per_subframe,
    )
    struct.pack_into("<I", header, 0x14, 2)
    struct.pack_into("<I", header, 0x18, 36000)
    struct.pack_into("<I", header, 0x24, 4)
    struct.pack_into("<I", header, 0x28, 1)
    struct.pack_into("<I", header, 0x2C, 1)

    out = bytearray(header)

    state = State()

    decoded_preview = []

    pos = 0

    frame_index = 0

    while pos < sample_count:
        frame_index += 1

        # State at the beginning of this frame.
        out += pack_state(state)

        for _ in range(2):
            if pos >= sample_count:
                break

            count = min(
                codes_per_subframe,
                sample_count - pos,
            )

            codes = []

            for sample in samples[
                pos:pos + count
            ]:
                code, decoded = choose_code(
                    sample,
                    state,
                )

                codes.append(code)
                decoded_preview.append(decoded)

            packed = pack_codes_4bit(codes)

            expected = (
                (count * 4) // 8
                + 1
            )

            if len(packed) != expected:
                raise RuntimeError(
                    f"subframe size mismatch: "
                    f"{len(packed)} != {expected}"
                )

            out += packed
            pos += count

    return (
        bytes(out),
        decoded_preview,
        subframe_count,
        last_count,
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("wav")
    parser.add_argument("output")

    parser.add_argument(
        "--template",
        required=True,
    )

    parser.add_argument(
        "--slot-size",
        type=int,
        default=None,
    )

    args = parser.parse_args()

    wav = Path(args.wav)
    output = Path(args.output)
    template_path = Path(args.template)

    samples = read_pcm(wav)
    template = template_path.read_bytes()

    encoded, preview, subframes, last = encode(
        samples,
        template,
    )

    if (
        args.slot_size is not None
        and len(encoded) != args.slot_size
    ):
        raise SystemExit(
            f"ERROR: encoded size {len(encoded)} "
            f"!= required slot size {args.slot_size}"
        )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_bytes(encoded)

    mse = sum(
        (a - b) ** 2
        for a, b in zip(samples, preview)
    ) / len(samples)

    peak_error = max(
        abs(a - b)
        for a, b in zip(samples, preview)
    )

    print("samples       :", len(samples))
    print("subframes     :", subframes)
    print("last subframe :", last)
    print("encoded bytes :", len(encoded))
    print("MSE           :", round(mse, 2))
    print("peak error    :", peak_error)
    print("output        :", output)


if __name__ == "__main__":
    main()

"""Regression tests for source preservation, exact cuts and review gating."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

import fisher_boundary_qa_v3 as qa


class SourceSafetyTests(unittest.TestCase):
    def test_slice_is_sample_exact_and_end_is_exclusive(self):
        pcm = np.arange(100, dtype='<i2')
        a, b, raw = qa.cut_samples(pcm, 10 / qa.RATE, 31 / qa.RATE)
        self.assertEqual((a, b), (10, 31))
        self.assertEqual(raw, pcm[10:31].tobytes())

    def test_invalid_intervals_fail_instead_of_truncating(self):
        pcm = np.zeros(100, dtype='<i2')
        for start, end in [(-.1, .1), (0, 1), (.001, .001), (.002, .001)]:
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                qa.cut_samples(pcm, start, end)

    def test_existing_wav_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'u000497_v03_candidate.wav'
            qa.save_cut(target, b'\0\0' * 100)
            before = target.read_bytes()
            with self.assertRaises(FileExistsError):
                qa.save_cut(target, b'\1\0' * 100)
            self.assertEqual(target.read_bytes(), before)

    def test_input_tampering_fails_before_build(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / 'source.mp3'
            target.write_bytes(b'original bytes')
            qa.write_tsv(root / 'input_snapshot.tsv', [dict(path=str(target), sha256=qa.sha(target))])
            with patch.object(qa, 'OUT', root):
                self.assertEqual(qa.check_inputs(), 1)
                target.write_bytes(b'changed bytes')
                with self.assertRaises(RuntimeError):
                    qa.check_inputs()

    def test_waveform_edges_distinguish_active_cut(self):
        pcm = np.zeros(qa.RATE, dtype='<i2')
        pcm[qa.RATE // 4:qa.RATE * 3 // 4] = 8000
        safe = qa.edge_metrics(pcm, .1, .9)
        unsafe = qa.edge_metrics(pcm, .4, .6)
        self.assertLess(safe['start_edge_dbfs'], -55)
        self.assertGreater(unsafe['start_edge_dbfs'], -20)
        self.assertGreater(safe['leading_quiet_ms'], 100)
        self.assertEqual(unsafe['leading_quiet_ms'], 0)

    def test_duplicate_lines_keep_distinct_source_times(self):
        clips = [dict(id='u000572', batch='B002', expected_text='Sen Ivan mısın?'),
                 dict(id='u000582', batch='B002', expected_text='Sen Ivan mısın?')]
        words = [dict(text=t, start=base+i*.2, end=base+(i+1)*.2)
                 for base in (157, 167) for i, t in enumerate(['Sen', 'Ivan', 'mısın'])]
        mapped = qa.aligned_words(clips, {'B002': {'result': {'words': words}}})
        self.assertEqual(mapped['u000572'][0]['start'], 157)
        self.assertEqual(mapped['u000582'][0]['start'], 167)


if __name__ == '__main__':
    unittest.main()

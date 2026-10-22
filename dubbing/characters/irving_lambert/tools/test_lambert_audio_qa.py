import tempfile
import unittest
from pathlib import Path

import numpy as np
import lambert_audio_qa as qa
from lambert_delivery import validate_partitions


class LambertSafetyTests(unittest.TestCase):
    def test_pilot_order_is_not_catalog_order(self):
        rows = [dict(id='u000314', expected_text='Kötü haber Fisher.'),
                dict(id='u000030', expected_text='Kahretsin Fisher.')]
        words = [dict(text=w, start=i, end=i+.5, source_key='pilot')
                 for i, w in enumerate(['Kötü', 'haber', 'Fisher.', 'Kahretsin', 'Fisher.'])]
        matched, unknown = qa.match_words(rows, words)
        self.assertEqual(matched['u000314'][0]['start'], 0)
        self.assertEqual(matched['u000030'][0]['start'], 3)
        self.assertFalse(unknown)

    def test_source_transition_is_kept_in_word_evidence(self):
        rows = [dict(id='a', expected_text='İlk kayıt.'), dict(id='b', expected_text='İkinci kayıt.')]
        words = [dict(text='İlk', start=400, end=401, source_key='one'),
                 dict(text='kayıt', start=401, end=402, source_key='one'),
                 dict(text='İkinci', start=0, end=1, source_key='two'),
                 dict(text='kayıt', start=1, end=2, source_key='two')]
        matched, _ = qa.match_words(rows, words)
        self.assertEqual(matched['a'][0]['source_key'], 'one')
        self.assertEqual(matched['b'][0]['source_key'], 'two')

    def test_tags_do_not_become_spoken_words(self):
        self.assertEqual(qa.spoken('[angry, commanding] Kahretsin, Fisher.'), 'Kahretsin, Fisher.')

    def test_no_silence_is_explicitly_flagged(self):
        boundary = qa.pick_boundary(1.0, 1.1, [])
        self.assertEqual(boundary['method'], 'NO_QUIET_BOUNDARY_NEEDS_REVIEW')

    def test_boundary_is_inside_the_interword_silence(self):
        boundary = qa.pick_boundary(1.0, 1.3, [(1.05, 1.25), (4, 5)])
        self.assertAlmostEqual(boundary['time'], 1.15)

    def test_exact_source_slice_and_overwrite_rejection(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'u000030_v01.wav'
            pcm = np.arange(1000, dtype='<i2')
            qa.save_cut(path, pcm, 100, 800)
            before = path.read_bytes()
            qa.save_cut(path, pcm, 100, 800)
            self.assertEqual(path.read_bytes(), before)
            with self.assertRaises(AssertionError):
                qa.save_cut(path, pcm, 101, 800)
            self.assertEqual(path.read_bytes(), before)

    def test_out_of_source_slice_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                qa.save_cut(Path(temp) / 'invalid.wav', np.zeros(10, dtype='<i2'), 0, 11)

    def partition_fixture(self):
        rows = []
        lengths = {}
        for source, count in enumerate([10, 79, 86, 32]):
            key = str(source)
            lengths[key] = count*100
            for i in range(count):
                rows.append(dict(id=f'{key}-{i}', source_key=key,
                    start_sample=i*100, end_sample_exclusive=(i+1)*100))
        return rows, lengths

    def test_four_sources_have_203_shared_boundaries(self):
        rows, lengths = self.partition_fixture()
        self.assertEqual(len(validate_partitions(rows, lengths)), 203)

    def test_source_sample_gap_or_overlap_is_rejected(self):
        for delta in [-1, 1]:
            rows, lengths = self.partition_fixture()
            rows[1]['start_sample'] += delta
            with self.assertRaises(AssertionError):
                validate_partitions(rows, lengths)

    def test_duplicate_delivery_id_is_rejected(self):
        rows, lengths = self.partition_fixture()
        rows[1]['id'] = rows[0]['id']
        with self.assertRaises(AssertionError):
            validate_partitions(rows, lengths)


if __name__ == '__main__':
    unittest.main()

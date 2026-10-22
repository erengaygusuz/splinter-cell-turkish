import tempfile
import unittest
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import vd001_audio_qa as qa
from vd001_delivery import validate_partition


class VD001SafetyTests(unittest.TestCase):
    def test_external_change_record_cannot_exempt_audio_from_protection(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name,allowed in [('.gitkeep',True),('original.wav',False)]:
                entry=dict(path=str(root/name),sha256=hashlib.sha256(b'').hexdigest())
                qa.write_tsv(root/'input_snapshot.tsv',[entry])
                (root/'workspace_changes.json').write_text(json.dumps(dict(removed=[entry])))
                with patch.object(qa,'QA',root):
                    if allowed:
                        self.assertEqual(qa.check_protected(),0)
                    else:
                        with self.assertRaises(AssertionError):
                            qa.check_protected()

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
        rows=[dict(id=f'u{i}',source_key='one' if i<3 else 'two',
            start_sample=(i if i<3 else i-3)*100,
            end_sample_exclusive=(i+1 if i<3 else i-2)*100,group_order=i+1) for i in range(5)]
        return rows, {'one':300,'two':200}, [r['id'] for r in rows]

    def test_partition_validates_each_source_separately(self):
        rows,lengths,ids=self.partition_fixture()
        self.assertEqual(len(validate_partition(rows,lengths,ids)),3)

    def test_missing_expected_line_cannot_pass(self):
        rows,lengths,ids=self.partition_fixture()
        with self.assertRaises(AssertionError):
            validate_partition(rows,lengths,ids+['missing'])

    def test_gap_and_overlap_are_rejected(self):
        for delta in [-1,1]:
            rows,lengths,ids=self.partition_fixture()
            rows[1]['start_sample']+=delta
            with self.assertRaises(AssertionError):
                validate_partition(rows,lengths,ids)

    def test_out_of_order_cut_ids_are_rejected(self):
        rows,lengths,ids=self.partition_fixture()
        rows[1]['group_order']=3
        with self.assertRaises(AssertionError):
            validate_partition(rows,lengths,ids)

    def test_trimmed_source_tail_requires_explicit_evidence(self):
        rows,lengths,ids=self.partition_fixture()
        rows[-1]['end_sample_exclusive']=190
        with self.assertRaises(AssertionError):
            validate_partition(rows,lengths,ids)
        tail={'two':dict(id='u4',start_sample=190,end_sample_exclusive=200)}
        self.assertEqual(len(validate_partition(rows,lengths,ids,tail)),3)

    def test_tail_evidence_cannot_hide_missing_samples_or_wrong_id(self):
        for ident,start,end in [('u3',190,200),('u4',191,200),('u4',190,199)]:
            rows,lengths,ids=self.partition_fixture()
            rows[-1]['end_sample_exclusive']=190
            tail={'two':dict(id=ident,start_sample=start,end_sample_exclusive=end)}
            with self.assertRaises(AssertionError):
                validate_partition(rows,lengths,ids,tail)


if __name__ == '__main__':
    unittest.main()

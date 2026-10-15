"""Offline presentation contract; all fixtures stay in the development skill."""
import json
import hashlib
from pathlib import Path
import tempfile
import unittest

import generate_polish_records as records


class PresentationTests(unittest.TestCase):
    def test_unit_boundaries(self):
        raw = '**Figure 1. Title.** First line (Supplementary Fig. S5) used 12 blocks.\nContinuation with 90% coverage.\n\n**Figure 2. Next.** Other.'
        row = {'unit_key': 'c1', 'type': '数字', 'original_sentences': ['**Figure 1.', 'S5) used 12 blocks.']}
        text = records.original_unit(row, raw)
        self.assertIn('First line (Supplementary Fig. S5) used 12 blocks.', text)
        self.assertIn('Continuation with 90% coverage.', text)
        self.assertNotIn('Figure 2', text)

    def test_numeric_sentences(self):
        raw = '# Heading\n\nWe used 0.5 px (Fig. S5) in 12 scans.\nThe following sentence has no number. Another 20 scans were held out.'
        row = {'unit_key': 2, 'type': '数字', 'original_sentences': ['S5) in 12 scans.']}
        self.assertEqual(records.original_unit(row, raw), 'We used 0.5 px (Fig. S5) in 12 scans.')

    def test_escape_and_truncation(self):
        self.assertEqual(records.cell('a<br>\nb | c', 10), 'a b &#124; c')
        self.assertTrue(records.cell('x' * 20, 10).endswith('…'))

    def test_unknown_gap_cannot_be_hidden(self):
        row = {'id': 'Q1', 'result': '来源待查', 'basis': 'The count differs between cohorts.'}
        with self.assertRaisesRegex(ValueError, 'triage'):
            records.triage_rows([row], {})

    def test_grouping_and_two_file_transaction(self):
        base = Path(__file__).resolve().parents[1] / '_dev' / 'fixes_batch8'
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as temp:
            root = Path(temp)
            process = root / '_process/Finalize/2026-10-15_polish_v5'
            process.mkdir(parents=True)
            (process/'before').mkdir()
            (process/'before/test.md').write_text('# Title\n\nA total of 12 scans were used.', encoding='utf-8')
            old = '# v5 作者裁决清单\n\n状态：待作者。\n\n## 沿用既有未决事项\n\nC002 未关闭。\n\n## 本轮来源待查\n\nold audit dump\n\n## 其他裁决与交付限制\n\n- F-WORD：保留。\n'
            (process/'作者裁决清单.md').write_text(old, encoding='utf-8')
            rows = [dict(id=f'N{i}', type='数字', file='test.md', position='block 2', unit_key=2,
                         original_sentences=['A total of 12 scans were used.'], result='来源待查',
                         basis='未在核查说明逐项复述，无法证明缺失。', evidence=[], conservative_action='保留原文。')
                    for i in range(1, 3)]
            (process/'crosscheck.json').write_text(json.dumps(rows), encoding='utf-8')
            triage = {'crosscheck_sha256': hashlib.sha256((process/'crosscheck.json').read_bytes()).hexdigest(),
                      'items': {r['id']: {'kind': 'coverage_gap', 'gap': '说明未逐项复述'} for r in rows}}
            output = records.render_records(process, triage)
            self.assertEqual(set(output), {'作者裁决清单.md', '附录_交叉核对审计.md'})
            text = output['作者裁决清单.md']
            self.assertIn('本轮需作者动作：0 组', text)
            self.assertIn('计数≠问题数', text)
            self.assertIn('C002 未关闭。', text)
            self.assertIn('- F-WORD：保留。', text)
            result = records.replace_records(root, process, output, '2026-10-15')
            self.assertEqual(len(result['record_changes']), 2)
            self.assertEqual(records.render_records(process, triage), output)
            second = records.replace_records(root, process, output, '2026-10-15')
            self.assertEqual(second['record_changes'], [])
            archive = root/'_archive/2026-10-15'/process.relative_to(root)/'作者裁决清单.md'
            self.assertEqual(archive.read_text(encoding='utf-8'), old)
            self.assertNotIn('<br>', output['附录_交叉核对审计.md'])

    def test_multiline_supplementary_and_table_boundaries(self):
        raw = '**Supplementary Figure S1. Title.**\nFirst paragraph.\n\nSecond paragraph with 10 scans.\n**Supplementary Figure S2. Next.** 20 scans.'
        row = dict(file='supp.md', unit_key='cS1', type='限定')
        self.assertEqual(records.original_unit(row, raw), '**Supplementary Figure S1. Title.** First paragraph. Second paragraph with 10 scans.')
        raw = '**Table 1. Title.**\nNotes in 12 eyes.\n**Supplementary Table S1. Next.** Notes.'
        self.assertEqual(records.original_unit(dict(row, unit_key='c1'), raw), '**Table 1. Title.** Notes in 12 eyes.')

    def test_path_traversal_and_archive_collision(self):
        base = Path(__file__).resolve().parents[1] / '_dev/fixes_batch8'
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as temp:
            root = Path(temp)
            with self.assertRaises(ValueError):
                records.safe_child(root, '../outside')
            process = root/'_process/Finalize/2026-10-15_polish_v5'
            process.mkdir(parents=True)
            (process/records.NAMES[0]).write_bytes(b'old')
            archive = root/'_archive/2026-10-15'/process.relative_to(root)/records.NAMES[0]
            archive.parent.mkdir(parents=True)
            archive.write_bytes(b'prior unrelated archive')
            before = records.snapshot(root)
            with self.assertRaisesRegex(ValueError, 'collision'):
                records.replace_records(root, process, {n: 'new' for n in records.NAMES}, '2026-10-15')
            self.assertEqual(records.snapshot(root), before)

    def test_stale_triage_rejected(self):
        base = Path(__file__).resolve().parents[1] / '_dev/fixes_batch8'
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as temp:
            process = Path(temp)
            (process/'crosscheck.json').write_text('[]', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'sha256'):
                records.render_records(process, {'items': {}, 'crosscheck_sha256': 'stale'})


if __name__ == '__main__':
    unittest.main()

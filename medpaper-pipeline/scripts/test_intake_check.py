"""Offline regression tests; all projects are built in temporary directories.

Run: python -X utf8 scripts/test_intake_check.py
Every case checks the real CLI's exit code as well as its diagnostics.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CHECKER = Path(__file__).with_name('intake_check.py')
HEADER = '| 序号 | 整理后路径 | 原路径 | 运行命令 | 前置序号 | 产出 | 对应图表 | 备注 |\n'
SEPARATOR = '|---|---|---|---|---|---|---|---|\n'


def row(rel, original='/original/source.py', note='', command='未知'):
    return f'| 01 | {rel} | {original} | {command} | — | — | — | {note} |\n'


class IntakeCheck(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='intake_check_')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / '01_analysis' / 'source-a'
        self.write('01_analysis/README.md', '# 来源\n- `source-a/`\n')
        self.write('01_analysis/source-a/README.md', '# 复现说明\n无回执；命令未知。\n')
        self.write('01_analysis/source-a/code/01_summarize.py', 'print("synthetic")\n')
        self.mapping(row('code/01_summarize.py'))

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
        return p

    def mapping(self, rows):
        (self.source / '映射表.md').write_text('# 映射表\n\n' + HEADER + SEPARATOR + rows, encoding='utf-8')

    def check(self, code=0, rule=None, plain=False):
        args = [sys.executable, '-X', 'utf8', str(CHECKER), str(self.root)]
        if not plain:
            args.append('--json')
        proc = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', check=False)
        self.assertEqual(proc.returncode, code, proc.stdout + proc.stderr)
        self.assertEqual(proc.stderr, '', proc.stderr)
        if plain:
            return proc.stdout
        result = json.loads(proc.stdout)
        if rule:
            self.assertIn(rule, [e['rule'] for e in result['errors']], result)
        return result

    def study(self, register=True):
        self.write('01_analysis/study-01/plans/plan.md', '# controller-owned\n')
        self.write('01_analysis/study-01/state.json', '{}\n')
        # A controlled study may contain unnumbered files and model checkpoints.
        self.write('01_analysis/study-01/runs/model.pth', 'synthetic placeholder\n')
        if register:
            self.write('01_analysis/README.md', '- `source-a/`\n- `study-01/`\n')

    def link(self, rel):
        target = self.write('outside_analysis/private.txt', 'must not be followed\n')
        link = self.root / rel
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            link.symlink_to(target)
        except OSError:
            if os.name != 'nt':
                raise
            # Junction creation does not require Windows symbolic-link privileges.
            proc = subprocess.run(['cmd', '/d', '/c', 'mklink', '/J', str(link), str(target.parent)],
                                  capture_output=True, check=False)
            self.assertEqual(proc.returncode, 0, repr(proc.stdout + proc.stderr))
        return link

    def test_compliant_passes(self):
        self.write('01_analysis/source-a/results/metrics.csv', 'metric,value\nscore,0.5\n')
        self.write('01_analysis/source-a/receipts/run.log', 'historical synthetic receipt\n')
        self.mapping(row('code/01_summarize.py') + row('results/metrics.csv') + row('receipts/run.log'))
        self.assertEqual(self.check(), {'errors': [], 'warnings': []})

    def test_missing_total_readme(self):
        (self.root / '01_analysis/README.md').unlink()
        self.check(1, 'index')

    def test_missing_source_readme(self):
        (self.source / 'README.md').unlink()
        self.check(1, 'structure')

    def test_missing_mapping_table(self):
        (self.source / '映射表.md').unlink()
        self.check(1, 'structure')

    def test_missing_code_directory(self):
        (self.source / 'code/01_summarize.py').unlink()
        (self.source / 'code').rmdir()
        self.check(1, 'structure')

    def test_missing_mapping_row(self):
        self.mapping('')
        self.check(1, 'unmapped-code')

    def test_unlisted_nested_code_file(self):
        self.write('01_analysis/source-a/code/nested/02_extra.py', '# extra\n')
        self.check(1, 'unmapped-code')

    def test_mapping_to_missing_file(self):
        self.mapping(row('code/01_summarize.py') + row('results/missing.csv'))
        self.check(1, 'missing-file')

    def test_invalid_name_even_when_mapped(self):
        p = self.source / 'code/01_summarize.py'
        p.rename(p.with_name('summarize.py'))
        self.mapping(row('code/summarize.py'))
        self.check(1, 'code-name')

    def test_blacklisted_extensions(self):
        for ext in ('.pt', '.pth', '.npz', '.safetensors', '.ckpt', '.bin', '.h5', '.sqlite', '.PTH'):
            with self.subTest(ext=ext):
                self.write('01_analysis/source-a/results/model' + ext, 'synthetic placeholder\n')
                self.mapping(row('code/01_summarize.py') + row('results/model' + ext))
                self.check(1, 'blacklist')
                (self.source / ('results/model' + ext)).unlink()

    def test_per_file_approval_allows_blacklist(self):
        self.write('01_analysis/source-a/results/approved.pth', 'synthetic placeholder\n')
        self.mapping(row('code/01_summarize.py') + row('results/approved.pth', note='作者批准：合成示例'))
        self.assertEqual(self.check()['errors'], [])

    def test_approval_in_other_column_does_not_allow(self):
        self.write('01_analysis/source-a/results/model.pth', 'synthetic placeholder\n')
        self.mapping(row('code/01_summarize.py', note='作者批准')
                     + row('results/model.pth', command='作者批准'))
        self.check(1, 'blacklist')

    def test_symlink_or_junction_rejected(self):
        self.link('01_analysis/source-a/code/02_link.py')
        result = self.check(1, 'symlink')
        self.assertNotIn('private.txt', json.dumps(result))

    def test_symlink_approval_never_exempts(self):
        self.link('01_analysis/source-a/results/approved.pth')
        self.mapping(row('code/01_summarize.py') + row('results/approved.pth', note='作者批准'))
        self.check(1, 'symlink')

    def test_symlinked_source_not_followed(self):
        self.link('01_analysis/linked-source')
        self.check(1, 'symlink')

    def test_study_unregistered(self):
        self.study(register=False)
        self.check(1, 'registration')

    def test_registered_study_keeps_controlled_structure(self):
        self.study()
        self.assertEqual(self.check(), {'errors': [], 'warnings': []})

    def test_partial_study_is_not_exempt(self):
        self.write('01_analysis/partial-study/plans/plan.md', '# incomplete\n')
        self.write('01_analysis/README.md', '- source-a\n- partial-study\n')
        self.check(1, 'structure')

    def test_directory_prefix_is_not_registration(self):
        self.write('01_analysis/README.md', '- source-a-old\n')
        self.check(1, 'registration')

    def test_blank_original_path(self):
        self.mapping(row('code/01_summarize.py', original=''))
        self.check(1, 'original-path')

    def test_traversal_and_absolute_destinations_rejected(self):
        for rel in ('code/../../outside.txt', '../outside.txt', '/code/absolute.py',
                    'C:/code/absolute.py', 'code/C:/foreign.py', 'other/file.csv'):
            with self.subTest(rel=rel):
                self.mapping(row('code/01_summarize.py') + row(rel))
                self.check(1, 'mapping-path' if rel != 'code/C:/foreign.py' else 'missing-file')

    def test_malformed_header_and_row(self):
        (self.source / '映射表.md').write_text('| file | original |\n|---|---|\n', encoding='utf-8')
        self.check(1, 'mapping-header')
        self.mapping('| 01 | code/01_summarize.py |\n')
        self.check(1, 'mapping-row')

    def test_duplicate_mapping(self):
        self.mapping(row('code/01_summarize.py') * 2)
        self.check(1, 'duplicate-path')

    def test_backslashes_backticks_and_escaped_command_pipe(self):
        self.mapping(row('`code\\01_summarize.py`', command=r'run \| log'))
        self.assertEqual(self.check()['errors'], [])

    def test_mapping_directory_is_not_a_file(self):
        (self.source / 'results').mkdir()
        self.mapping(row('code/01_summarize.py') + row('results/'))
        self.check(1, 'mapping-path')

    def test_warning_keeps_zero_exit(self):
        (self.source / 'code/01_summarize.py').unlink()
        self.mapping('')
        result = self.check()
        self.assertEqual(result['errors'], [])
        self.assertEqual([w['rule'] for w in result['warnings']], ['empty-code'])

    def test_external_repository_readme_only(self):
        temp = tempfile.TemporaryDirectory(prefix='intake_external_')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.write('01_analysis/README.md', '作者选择不迁移；外部路径和 commit 仅记录、不读取。\n')
        self.assertEqual(self.check(), {'errors': [], 'warnings': []})

    def test_plain_output_reports_error_and_summary(self):
        self.mapping('')
        output = self.check(1, plain=True)
        self.assertIn('[error]', output)
        self.assertIn('hit(s), 0 warning(s)', output)


if __name__ == '__main__':
    unittest.main(verbosity=2)

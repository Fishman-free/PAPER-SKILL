#!/usr/bin/env node
'use strict';

/**
 * cumcm-paper-skill 安装器
 *
 * 把 skill/ 目录下的技能文件安装到 Claude Code 的技能目录：
 *   - 用户级（默认）：~/.claude/skills/cumcm-paper/
 *   - 项目级（--project）：./.claude/skills/cumcm-paper/
 *
 * 用法：
 *   npx cumcm-paper-skill            # 安装到用户级
 *   npx cumcm-paper-skill --project  # 安装到当前项目
 *   npx cumcm-paper-skill --force    # 覆盖已存在的安装
 *   npx cumcm-paper-skill --uninstall
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const SKILL_NAME = 'cumcm-paper';
const PKG_ROOT = path.resolve(__dirname, '..');
const SRC_SKILL = path.join(PKG_ROOT, 'skill', SKILL_NAME);
// LaTeX 模板随 skill 一起安装，放在 skill 目录内，保证 SKILL.md 的相对引用不断链
const SRC_TEMPLATE = path.join(PKG_ROOT, 'assets', 'latex-template');
const TEMPLATE_SUBDIR = 'assets/latex-template';

const args = process.argv.slice(2);
const has = (flag) => args.includes(flag);
const OPT = {
  project: has('--project') || has('-p'),
  force: has('--force') || has('-f'),
  uninstall: has('--uninstall') || has('-u'),
  silent: has('--silent') || has('-s'),
  help: has('--help') || has('-h'),
};

const C = {
  reset: '\x1b[0m',
  bold: '\x1b[1m',
  dim: '\x1b[2m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  cyan: '\x1b[36m',
};

function log(msg) {
  if (!OPT.silent) console.log(msg);
}

function printHelp() {
  console.log(`
${C.bold}cumcm-paper-skill${C.reset} — 中国大学生数学建模竞赛论文写作 Skill

${C.bold}用法${C.reset}
  npx cumcm-paper-skill [选项]

${C.bold}选项${C.reset}
  -p, --project     安装到当前项目的 .claude/skills/（默认为用户级）
  -f, --force       覆盖已存在的安装
  -u, --uninstall   卸载
  -s, --silent      静默模式
  -h, --help        显示帮助

${C.bold}安装位置${C.reset}
  用户级: ${path.join(os.homedir(), '.claude', 'skills', SKILL_NAME)}
  项目级: ${path.join(process.cwd(), '.claude', 'skills', SKILL_NAME)}
`);
}

function targetDir() {
  const base = OPT.project
    ? path.join(process.cwd(), '.claude', 'skills')
    : path.join(os.homedir(), '.claude', 'skills');
  return path.join(base, SKILL_NAME);
}

function copyRecursive(src, dest) {
  const stat = fs.statSync(src);
  if (stat.isDirectory()) {
    fs.mkdirSync(dest, { recursive: true });
    for (const entry of fs.readdirSync(src)) {
      copyRecursive(path.join(src, entry), path.join(dest, entry));
    }
  } else {
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.copyFileSync(src, dest);
  }
}

function countFiles(dir) {
  let n = 0;
  for (const entry of fs.readdirSync(dir)) {
    const p = path.join(dir, entry);
    if (fs.statSync(p).isDirectory()) n += countFiles(p);
    else n += 1;
  }
  return n;
}

function main() {
  if (OPT.help) {
    printHelp();
    return;
  }

  const dest = targetDir();

  if (OPT.uninstall) {
    if (!fs.existsSync(dest)) {
      log(`${C.yellow}未找到安装目录：${dest}${C.reset}`);
      return;
    }
    fs.rmSync(dest, { recursive: true, force: true });
    log(`${C.green}✓ 已卸载${C.reset} ${dest}`);
    return;
  }

  if (!fs.existsSync(SRC_SKILL)) {
    console.error(`${C.red}✗ 找不到技能源目录：${SRC_SKILL}${C.reset}`);
    process.exit(1);
  }

  if (fs.existsSync(dest) && !OPT.force) {
    log(`${C.yellow}⚠ 已存在：${dest}${C.reset}`);
    log(`${C.dim}  使用 --force 覆盖，或 --uninstall 先卸载${C.reset}`);
    return;
  }

  if (fs.existsSync(dest)) fs.rmSync(dest, { recursive: true, force: true });

  // 1) 技能主体（SKILL.md / references / scripts）
  copyRecursive(SRC_SKILL, dest);

  // 2) LaTeX 模板 — 必须装进 skill 目录内，否则 SKILL.md 里的相对引用会断链
  const tplDest = path.join(dest, TEMPLATE_SUBDIR);
  let tplCount = 0;
  if (fs.existsSync(SRC_TEMPLATE)) {
    copyRecursive(SRC_TEMPLATE, tplDest);
    tplCount = countFiles(tplDest);
  }

  const n = countFiles(dest);
  log(`${C.green}✓ 安装完成${C.reset}`);
  log(`  ${C.dim}位置:${C.reset} ${dest}`);
  log(`  ${C.dim}文件:${C.reset} ${n} 个` +
      (tplCount ? `（含 LaTeX 模板 ${tplCount} 个）` : ''));
  if (!tplCount) {
    log(`  ${C.yellow}⚠ 未找到 LaTeX 模板，模板相关的相对引用将不可用${C.reset}`);
  }
  log('');
  log(`  ${C.cyan}在 Claude Code 中试试：${C.reset}`);
  log(`  ${C.dim}· 帮我检查这篇国赛论文的摘要${C.reset}`);
  log(`  ${C.dim}· 国赛论文的模型假设该怎么写${C.reset}`);
  log(`  ${C.dim}· 用国赛模板搭一篇论文骨架${C.reset}`);
}

main();

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub 工具箱 v2.0 — Streamlit 版
美观交互 · 完整功能 · 可配置仓库 · 模块化扩展架构
"""

import os, sys, json, subprocess, shutil, tempfile, time, textwrap, uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

import streamlit as st
from streamlit_option_menu import option_menu

# ==================== 常量 ====================
APP_DIR = Path(__file__).parent
CONFIG_FILE = APP_DIR / "github工具箱_config.json"
LOG_FILE = APP_DIR / "github工具箱_log.txt"

DEFAULT_CONFIG = {
    "repo_dir": "",
    "branch": "main",
    "github_repo": "",
    "delete_local_copy": True,
}

# ==================== 工具函数 ====================

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                for k, v in DEFAULT_CONFIG.items():
                    cfg.setdefault(k, v)
                return cfg
        except Exception:
            return dict(DEFAULT_CONFIG)
    return dict(DEFAULT_CONFIG)

def save_config(cfg: dict):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def log_msg(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}] {msg}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass

def run_git(cmd: list[str], cwd: str, timeout: int = 60) -> tuple[bool, str, str]:
    try:
        r = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "命令执行超时"
    except Exception as e:
        return False, "", str(e)

def check_repo(repo_dir: str) -> bool:
    return bool(repo_dir) and (Path(repo_dir) / ".git").exists()

def format_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

def short_path(p: str, max_len: int = 50) -> str:
    return p if len(p) <= max_len else "..." + p[-(max_len - 3):]

def find_local_repo(github_repo: str) -> str:
    """根据 GitHub 仓库名自动寻找本地仓库路径"""
    if not github_repo or "/" not in github_repo:
        return ""
    repo_name = github_repo.split("/")[-1]
    user = os.environ.get("USERPROFILE") or os.environ.get("HOME", "")
    candidates = [
        os.path.join(user, "Desktop", repo_name),
        os.path.join(user, "Desktop", "111", repo_name),
        os.path.join(user, "Documents", repo_name),
        os.path.join(user, "github", repo_name),
        os.path.join(user, "repos", repo_name),
        os.path.join(user, "Desktop", "1234", repo_name),
    ]
    for p in candidates:
        if os.path.isdir(os.path.join(p, ".git")):
            return p
    # 如果没找到，返回最可能的桌面路径作为默认值
    return os.path.join(user, "Desktop", repo_name)

def on_github_repo_change():
    """github_repo 输入变化时自动检测本地路径"""
    val = st.session_state.get("gh_repo_input", "").strip()
    if val and "/" in val:
        found = find_local_repo(val)
        if found:
            st.session_state.gh_detected_path = found

def _do_clone(github_repo: str, dest_path: str):
    """执行 git clone 并将结果存入 session_state"""
    if not github_repo or "/" not in github_repo:
        st.error("请先输入有效的 GitHub 仓库地址。")
        return
    if not dest_path.strip():
        st.error("请指定克隆目标路径。")
        return

    dest = Path(dest_path.strip())
    repo_name = github_repo.split("/")[-1]

    # 如果目标路径已存在且不是以仓库名结尾，自动追加仓库名目录
    if dest.exists() and dest.name != repo_name:
        dest = dest / repo_name

    if dest.exists() and not dest.is_dir():
        st.error("目标路径已存在且不是目录。")
        return
    if (dest / ".git").exists():
        st.success("该目录已是 Git 仓库，无需克隆。")
        st.session_state._cloned_path = str(dest)
        st.session_state.gh_detected_path = str(dest)
        st.rerun()
        return

    url = f"https://github.com/{github_repo}.git"
    parent = str(dest.parent)

    with st.status(f"⏳ 正在克隆 {github_repo}...", expanded=True) as status:
        st.write(f"📥 从 {url} 克隆到 {dest}")
        st.write("📂 创建目录...")
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            status.update(label="❌ 目录创建失败", state="error")
            st.error(str(e))
            return

        st.write("📦 git clone 进行中...")
        ok, out, err = run_git(
            ["git", "clone", url, str(dest)],
            parent, timeout=180
        )

        if ok:
            status.update(label="✅ 克隆成功！", state="complete")
            st.success(f"✅ 仓库已克隆到: {dest}")
            log_msg(f"克隆成功: {github_repo} -> {dest}")
            # 保存到 session_state，表单会读取它
            st.session_state._cloned_path = str(dest)
            st.session_state.gh_detected_path = str(dest)
            st.rerun()
        else:
            status.update(label="❌ 克隆失败", state="error")
            st.error(f"克隆失败: {err}")
            log_msg(f"克隆失败: {github_repo} -> {err}")

def init_state():
    defaults = {
        "cfg": load_config(),
        "page": "首页",
        "upload_paths": [],
        "upload_done": False,   # 标记上传刚完成，阻止 file_uploader 重复添加
        "delete_selected": [],      # 批量选择
        "delete_confirm": None,
        "del_key_ver": 0,           # checkbox key 版本号（全选时刷新）
        "op_log": [],
        "repo_status": {},
        "tree_expanded": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ==================== CSS ====================
CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * { font-family: 'Inter', -apple-system, sans-serif; }
    .stApp { background: #f0f2f6; }
    .block-container { padding: 1.2rem 2rem 2rem 2rem; max-width: 1200px; }

    section[data-testid="stSidebar"] > div:first-child { padding-top: 0; background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%); }
    section[data-testid="stSidebar"] * { color: #e0e0e0 !important; }
    .sidebar-mini { padding: 20px 16px 8px 16px; text-align: center; }
    .sidebar-mini .logo { font-size: 28px; }
    .sidebar-footer { padding: 12px 16px; border-top: 1px solid #2a2a4a; margin-top: 4px; }
    .sidebar-footer p { color: #667788 !important; font-size: 11px; text-align: center; }

    /* GitHub 账户卡片 */
    .gh-profile { background: #fff; border-radius: 14px; padding: 28px 24px; border: 1px solid #e8ecf0; display: flex; align-items: center; gap: 20px; }
    .gh-avatar { width: 60px; height: 60px; border-radius: 50%; background: linear-gradient(135deg, #0d6efd, #6610f2); display: flex; align-items: center; justify-content: center; font-size: 28px; color: #fff; font-weight: 700; flex-shrink: 0; }
    .gh-info h2 { margin: 0; font-size: 22px; font-weight: 700; }
    .gh-info p { margin: 2px 0 0 0; color: #666; font-size: 14px; }

    .badge { display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; }
    .badge-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .badge-warning { background: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
    .badge-danger { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    .badge-info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }

    .feature-card { background: #fff; border-radius: 12px; padding: 20px 24px; border: 1px solid #e8ecf0; transition: all .2s; }
    .feature-card:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0,0,0,.08); border-color: #0d6efd; }
    .feature-card h3 { margin: 0 0 6px 0; font-size: 17px; font-weight: 700; }
    .feature-card p { margin: 0; color: #666; font-size: 13px; line-height: 1.5; }

    .stat-box { background: #fff; border-radius: 10px; padding: 16px; text-align: center; border: 1px solid #e8ecf0; }
    .stat-box .num { font-size: 28px; font-weight: 700; color: #0d6efd; }
    .stat-box .label { font-size: 12px; color: #888; margin-top: 2px; }

    .file-item { display: flex; align-items: center; gap: 12px; padding: 8px 12px; background: #fff; border-radius: 8px; border: 1px solid #eee; margin-bottom: 4px; }
    .file-item:hover { background: #f8f9fa; }

    .tree-item { display: flex; align-items: center; padding: 6px 8px; border-radius: 6px; transition: background .12s; }
    .tree-item:hover { background: #f0f4ff; }
    .tree-item.selected { background: #e0ecff; }
    .tree-name { flex: 1; font-size: 14px; font-weight: 500; }
    .tree-meta { color: #999; font-size: 12px; margin-left: 12px; }

    .log-entry { padding: 6px 10px; border-left: 3px solid #0d6efd; background: #f8f9fa; border-radius: 0 6px 6px 0; margin-bottom: 4px; font-size: 13px; }
    .log-entry.error { border-left-color: #dc3545; background: #fff5f5; }
    .log-entry.success { border-left-color: #28a745; background: #f0fff4; }

    .wizard-step { background: #fff; border-radius: 16px; padding: 32px; border: 1px solid #e8ecf0; max-width: 640px; margin: 0 auto; }
    .wizard-step h2 { margin: 0 0 8px 0; font-size: 22px; }
    .wizard-step p { color: #666; font-size: 14px; margin-bottom: 20px; }

    hr { margin: 1.5rem 0; }
    .stButton button { font-weight: 600; border-radius: 8px; }
    div[data-testid="stSidebarNav"] { display: none; }
    .stProgress > div > div { background-color: #0d6efd; }
</style>
"""

# ==================== 页面：配置向导 ====================

def page_home():
    cfg = st.session_state.cfg
    repo_ok = check_repo(cfg["repo_dir"])
    has_config = bool(cfg.get("github_repo"))

    # 获取 Git 账户信息
    git_name = ""
    git_email = ""
    if repo_ok:
        ok, out, _ = run_git(["git", "config", "user.name"], cfg["repo_dir"])
        if ok: git_name = out
        ok, out, _ = run_git(["git", "config", "user.email"], cfg["repo_dir"])
        if ok: git_email = out

    # 取 GitHub 用户名（从 remote url 或配置）
    gh_user = ""
    if has_config:
        gh_user = cfg["github_repo"].split("/")[0] if "/" in cfg["github_repo"] else ""

    display_name = git_name or gh_user or "未设置"
    initial = display_name[0].upper() if display_name and display_name != "未设置" else "?"
    info_lines = []
    if git_email: info_lines.append(git_email)
    if gh_user: info_lines.append(f"github.com/{gh_user}")
    info_str = " · ".join(info_lines) if info_lines else "请先在设置中配置 Git 账户"

    # GitHub 账户卡片
    st.markdown(
        f"""
        <div class="gh-profile">
            <div class="gh-avatar">{initial}</div>
            <div class="gh-info">
                <h2>{display_name}</h2>
                <p>{info_str}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    # 仓库状态栏
    if not has_config:
        st.markdown('<div class="badge badge-danger">⚠️ 未配置仓库</div>', unsafe_allow_html=True)
    elif repo_ok:
        st.markdown(f'<div class="badge badge-success">✅ 仓库就绪 · {short_path(cfg["repo_dir"], 40)}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="badge badge-warning">⚠️ 仓库不可用 · {short_path(cfg["repo_dir"], 40)}</div>', unsafe_allow_html=True)

    st.markdown("---")

    # 统计面板（与 GitHub 远程保持一致）
    stats = [0, 0, 0, 0]
    if repo_ok:
        try:
            # 文件数：只统计 Git 跟踪的文件
            ok, out, _ = run_git(["git", "ls-files"], cfg["repo_dir"])
            total_files = len([f for f in out.split("\n") if f.strip()]) if ok else 0

            # 文件夹数：跟踪文件所在的不同目录数
            dirs = set()
            for f in out.split("\n"):
                f = f.strip()
                if "/" in f:
                    dirs.add(f.rsplit("/", 1)[0])
            total_dirs = len(dirs)

            # 提交数 & 最新 Commit：使用远程分支数据
            ok, out, _ = run_git(["git", "rev-list", "--count", f"origin/{cfg['branch']}"], cfg["repo_dir"])
            commits = int(out) if ok and out else 0
            if not ok or commits == 0:
                # 回退到本地分支
                ok, out, _ = run_git(["git", "rev-list", "--count", cfg["branch"]], cfg["repo_dir"])
                commits = int(out) if ok and out else 0

            ok2, out2, _ = run_git(["git", "rev-parse", "--short", f"origin/{cfg['branch']}"], cfg["repo_dir"])
            last = out2[:7] if ok2 and out2 else "-"
            if last == "-":
                ok2, out2, _ = run_git(["git", "rev-parse", "--short", cfg["branch"]], cfg["repo_dir"])
                last = out2[:7] if ok2 and out2 else "-"

            stats = [total_files, total_dirs, commits, last]
        except Exception:
            pass

    cols = st.columns(4)
    labels = ["文件数", "文件夹", "提交数", "最新 Commit"]
    for col, label, val in zip(cols, labels, stats):
        with col:
            st.markdown(f'<div class="stat-box"><div class="num">{val}</div><div class="label">{label}</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # 快速入口 — 仅打开仓库
    st.markdown("##### 📂 快速入口")
    if has_config:
        st.markdown(f'<div class="feature-card"><div style="display:flex;align-items:center;gap:12px;"><span style="font-size:32px;">🌐</span><div><h3>打开仓库</h3><p>在浏览器中打开 GitHub 远程仓库页面。</p></div></div></div>', unsafe_allow_html=True)
        url = f"https://github.com/{cfg['github_repo']}"
        if st.button("🌐 打开仓库", key="btn_open_repo", use_container_width=True, type="primary"):
            import webbrowser
            webbrowser.open(url)
            st.success(f"已打开: {url}")
    else:
        st.info("💡 仓库尚未配置，请先配置仓库以使用功能。")
        c1, c2, _ = st.columns([1, 1, 2])
        with c1:
            if st.button("⚙️ 前往设置", type="primary", use_container_width=True):
                st.session_state.page = "settings"; st.rerun()
        with c2:
            if st.button("📖 查看指南", use_container_width=True):
                st.session_state.page = "settings"; st.rerun()

    st.markdown("---")

    # 未来功能
    with st.expander("🔮 未来功能预览（扩展接口）", expanded=False):
        futures = [
            ("📝 批量提交信息生成", "AI 辅助生成规范的 Git 提交信息"),
            ("🌿 分支管理", "创建、切换、合并、删除分支"),
            ("🔄 自动同步与回滚", "一键同步远程、回滚到历史版本"),
            ("🔀 PR 管理", "查看、创建、合并 Pull Request"),
            ("📋 Issue 看板", "管理仓库 Issue，支持看板视图"),
            ("📊 仓库统计", "代码行数、贡献者、活跃度可视化"),
        ]
        cf = st.columns(3)
        for i, (t, d) in enumerate(futures):
            with cf[i % 3]:
                st.markdown(f"**{t}**  \n{d}", help="预留接口，待实现")


def page_upload():
    cfg = st.session_state.cfg
    if not check_repo(cfg["repo_dir"]):
        st.markdown('<div class="badge badge-warning" style="margin-bottom:16px;">⚠️ 仓库不可用</div>', unsafe_allow_html=True)
        st.error(f"未找到本地仓库：{cfg['repo_dir']}")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("⚙️ 前往设置"): st.session_state.page = "settings"; st.rerun()
        with c2:
            if st.button("🏠 返回首页"): st.session_state.page = "首页"; st.rerun()
        return

    st.markdown("## 📤 上传文件到 GitHub")
    st.markdown(f'<span class="badge badge-info">📦 {cfg["github_repo"]} / {cfg["branch"]}</span>', unsafe_allow_html=True)
    st.markdown("---")

    # 方式一：文件上传器
    st.markdown("##### 📎 选择文件（浏览器上传）")
    uploaded = st.file_uploader("选择文件上传", accept_multiple_files=True, label_visibility="collapsed", key="fu_main")
    if uploaded and not st.session_state.get("upload_done", False):
        repo_dir = Path(cfg["repo_dir"])
        for f in uploaded:
            dest = repo_dir / f.name
            try:
                with open(dest, "wb") as fh: fh.write(f.getbuffer())
                if str(dest) not in st.session_state.upload_paths:
                    st.session_state.upload_paths.append(str(dest))
            except Exception as e:
                st.error(f"保存 {f.name} 失败: {e}")
    elif uploaded and st.session_state.get("upload_done", False):
        pass

    # 方式二：本地路径（支持文件夹）
    st.markdown("---")
    st.markdown("##### 📂 指定本地路径（支持文件夹）")
    col_path, col_add = st.columns([3, 1])
    with col_path:
        local_path = st.text_input("本地文件或文件夹路径", placeholder="C:\\Users\\...\\myfile.txt 或 C:\\...\\myfolder", label_visibility="collapsed", key="local_path_input")
    with col_add:
        if st.button("➕ 添加到列表", use_container_width=True):
            _add_local_path(local_path)

    paths = st.session_state.upload_paths
    st.markdown(f"---\n##### 📋 待上传列表 ({len(paths)} 项)")
    if paths:
        for i, p in enumerate(paths):
            is_dir = os.path.isdir(p)
            icon = "📁" if is_dir else "📄"
            sz = ""
            try: sz = format_size(os.path.getsize(p)) if not is_dir else ""
            except: sz = "?"
            cols = st.columns([5, 1, 1, 1])
            with cols[0]:
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:8px;"><span>{icon}</span> '
                    f'<strong>{Path(p).name}</strong> '
                    f'<span style="color:#999;font-size:12px;margin-left:8px;">{short_path(p, 45)}</span></div>',
                    unsafe_allow_html=True)
            with cols[1]: st.caption(sz if sz else ("📁文件夹" if is_dir else ""))
            with cols[2]: st.caption("待上传")
            with cols[3]:
                if st.button("✕", key=f"rm_up_{i}", help="移除"):
                    st.session_state.upload_paths.pop(i); st.rerun()

        st.markdown("---")
        commit_msg = st.text_input("提交信息（可选）", placeholder="留空自动生成", key="commit_msg")
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("🚀 开始上传", type="primary", use_container_width=True):
                with st.status("⏳ 正在上传...", expanded=True) as status:
                    st.write("📁 复制文件到本地仓库...")
                    result = _do_upload(paths, cfg, commit_msg.strip())
                    if result["success"]:
                        status.update(label="✅ 上传成功！", state="complete")
                    else:
                        status.update(label="❌ 上传失败", state="error")
                    for line in result.get("details", []): st.write(line)
                if result["success"]:
                    st.success(result["message"])
                    st.session_state.upload_paths = []
                    st.session_state.upload_done = True
                    st.rerun()
                else:
                    st.error(result["message"])
        with col_b2:
            if st.button("🗑️ 清空列表", use_container_width=True):
                st.session_state.upload_paths = []; st.session_state.upload_done = False; st.rerun()
    else:
        st.info("💡 请通过上方区域选择要上传的文件。")
        st.session_state.upload_done = False


def _do_upload(paths: list[str], cfg: dict, commit_msg: str = "") -> dict:
    """
    执行上传：
    1. 将 paths 中的文件/文件夹复制到仓库目录（类似原批处理脚本）
    2. git add . → git commit → git push
    3. 如启用清理，则删除本地副本
    """
    repo_dir = cfg["repo_dir"]
    list_file = os.path.join(tempfile.gettempdir(), f"ul_{uuid.uuid4().hex[:8]}.txt")
    details = []; item_count = 0; errors = []

    for src in paths:
        sp = Path(src)
        if not sp.exists():
            errors.append(f"跳过（不存在）: {src}")
            continue
        dest = Path(repo_dir) / sp.name
        try:
            if sp.is_dir():
                if dest.exists():
                    for f in sp.rglob("*"):
                        if f.is_file():
                            rel = f.relative_to(sp)
                            target = dest / rel
                            target.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(f, target)
                else:
                    shutil.copytree(sp, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(sp, dest)
            with open(list_file, "a", encoding="utf-8") as lf:
                lf.write(sp.name + "\n")
            item_count += 1
            details.append(f"✅ 已复制: {sp.name}")
        except Exception as e:
            errors.append(f"复制 {sp.name} 失败: {e}")

    if item_count == 0:
        log_msg("上传失败: 没有成功复制任何文件")
        return {"success": False, "message": "没有成功复制任何文件。", "details": details + errors}

    details.append("📌 git add...")
    ok, out, err = run_git(["git", "add", "."], repo_dir)
    if not ok:
        log_msg(f"git add 失败: {err}")
        return {"success": False, "message": f"git add 失败: {err}", "details": details + [f"❌ {err}"]}

    msg = commit_msg or f"上传 {item_count} 个文件"
    details.append(f"📌 git commit -m \"{msg}\"")
    run_git(["git", "commit", "-m", msg], repo_dir)

    details.append("📤 git push...")
    ok, out, err = run_git(["git", "push", "origin", cfg["branch"]], repo_dir, timeout=120)
    if not ok:
        log_msg(f"推送失败: {err}")
        return {"success": False, "message": f"推送失败: {err}", "details": details + [f"❌ {err}"]}

    # 清理本地副本（如启用，类似原批处理脚本）
    if cfg.get("delete_local_copy", True) and os.path.exists(list_file):
        with open(list_file, "r", encoding="utf-8") as f:
            items = [line.strip() for line in f if line.strip()]
        for item in items:
            target = Path(repo_dir) / item
            if target.exists():
                try:
                    if target.is_dir():
                        shutil.rmtree(target)
                    else:
                        target.unlink()
                except Exception:
                    pass
            run_git(["git", "checkout", "--", item], repo_dir)
        try:
            os.remove(list_file)
        except Exception:
            pass
        details.append("🧹 本地副本已清理")

    log_msg(f"上传成功: {item_count} 个项目 -> {cfg['github_repo']}")
    msg = f"✅ 成功上传 {item_count} 个项目！"
    if errors:
        msg += "\n" + "\n".join(errors)
    return {"success": True, "message": msg, "details": details}


def _add_local_path(path: str):
    """将本地文件或文件夹路径添加到上传列表"""
    path = path.strip().strip('"').strip("'")
    if not path:
        st.error("请输入有效的路径。")
        return
    p = Path(path)
    if not p.exists():
        st.error(f"路径不存在: {path}")
        return
    if str(p) not in st.session_state.upload_paths:
        st.session_state.upload_paths.append(str(p))
        kind = "文件夹" if p.is_dir() else "文件"
        st.success(f"✅ 已添加{kind}: {p.name}")
        st.rerun()
    else:
        st.info(f"已在列表中: {p.name}")


def page_delete():
    cfg = st.session_state.cfg
    if not check_repo(cfg["repo_dir"]):
        st.error("⚠️ 未找到本地仓库，请先在设置中配置。")
        if st.button("⚙️ 前往设置"): st.session_state.page = "settings"; st.rerun()
        return

    st.markdown("## 🗑️ 删除仓库中的文件")
    st.markdown(f'<span class="badge badge-info">📦 {cfg["github_repo"]} / {cfg["branch"]}</span>', unsafe_allow_html=True)
    st.markdown("---")

    tcols = st.columns([3, 1, 1])
    with tcols[0]:
        search = st.text_input("🔍", placeholder="搜索文件或文件夹...", label_visibility="collapsed", key="del_search")
    with tcols[1]: st.caption("点击同步远程")
    with tcols[2]:
        if st.button("🔄 同步", use_container_width=True):
            with st.spinner("正在同步..."):
                run_git(["git", "fetch", "origin", cfg["branch"]], cfg["repo_dir"])
                run_git(["git", "checkout", cfg["branch"]], cfg["repo_dir"])
                run_git(["git", "pull", "origin", cfg["branch"]], cfg["repo_dir"])
            st.success("同步完成"); st.rerun()

    repo_path = Path(cfg["repo_dir"])
    def _skip(name): return name.startswith(".") or name in ("__pycache__", ".venv", "node_modules", ".git")
    def _build_flat(path, prefix=""):
        items = []
        try:
            entries = sorted([p for p in path.iterdir() if not _skip(p.name)], key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError: return items
        for entry in entries:
            is_dir = entry.is_dir()
            rel = (Path(prefix) / entry.name).as_posix() if prefix else entry.name
            try:
                stt = entry.stat(); size = stt.st_size
                mtime = datetime.fromtimestamp(stt.st_mtime).strftime("%Y-%m-%d %H:%M")
            except: size = 0; mtime = ""
            items.append({"name": entry.name, "path": rel, "is_dir": is_dir, "size": format_size(size) if not is_dir else "", "mtime": mtime, "level": prefix.count("/") if prefix else 0})
            if is_dir: items.extend(_build_flat(entry, rel))
        return items

    all_items = _build_flat(repo_path)
    if search: all_items = [d for d in all_items if search.lower() in d["name"].lower()]
    if not all_items:
        st.info("仓库为空或没有可显示的文件。"); return

    selected = st.session_state.get("delete_selected", [])
    if not isinstance(selected, list): selected = []

    st.markdown("##### 文件列表")
    st.caption("勾选要删除的文件/文件夹，然后点击底部「批量删除」")

    # 全选/取消（带 key 版本刷新）
    col_sel_all, col_sel_none, col_count = st.columns([1, 1, 4])
    with col_sel_all:
        if st.button("☑️ 全选", use_container_width=True):
            st.session_state.delete_selected = [d["path"] for d in all_items]
            st.session_state.del_key_ver += 1
            st.rerun()
    with col_sel_none:
        if st.button("⬜ 取消全选", use_container_width=True):
            st.session_state.delete_selected = []
            st.session_state.del_key_ver += 1
            st.rerun()
    with col_count:
        st.markdown(f"<div style='text-align:right;color:#888;font-size:13px;padding-top:4px;'>已选择 <strong>{len(selected)}</strong> 项</div>", unsafe_allow_html=True)

    kv = st.session_state.get("del_key_ver", 0)
    for idx, item in enumerate(all_items):
        is_checked = item["path"] in selected
        checked = st.checkbox(
            label=f'{"📁 " if item["is_dir"] else "📄 "}{item["name"]}  {item["size"]}  {item["mtime"]}',
            value=is_checked,
            key=f"cb_del_{kv}_{idx}",
        )
        if checked and item["path"] not in selected:
            selected.append(item["path"])
            st.session_state.delete_selected = selected
        elif not checked and item["path"] in selected:
            selected.remove(item["path"])
            st.session_state.delete_selected = selected

    st.markdown("---")
    st.markdown(f"已选择 **{len(selected)}** 项")

    if selected:
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            if st.button("🗑️ 批量删除", type="primary", use_container_width=True):
                st.session_state.delete_confirm = {"paths": list(selected)}; st.rerun()
        with c2:
            if st.button("取消选择", use_container_width=True):
                st.session_state.delete_selected = []; st.rerun()

    confirm = st.session_state.get("delete_confirm")
    if confirm:
        paths = confirm["paths"]
        st.markdown("---")
        st.error(f"⚠️ **即将批量删除以下 {len(paths)} 项：**\n\n" + "\n".join(f"`{p}`" for p in paths) + "\n\n此操作将同步到远程仓库，**不可恢复**！")
        col_y, col_n = st.columns(2)
        with col_y:
            if st.button("✅ 确认删除", type="primary", use_container_width=True):
                with st.status("⏳ 正在批量删除...", expanded=True) as status:
                    success_count = 0
                    fail_count = 0
                    for del_path in paths:
                        is_dir = any(d["path"] == del_path and d["is_dir"] for d in all_items)
                        full_path = Path(cfg["repo_dir"]) / del_path
                        st.write(f"📌 删除: {del_path}")

                        # 先检查文件是否被 git 跟踪
                        ok_tracked, out, _ = run_git(["git", "ls-files", del_path], cfg["repo_dir"])
                        is_tracked = ok_tracked and bool(out.strip())

                        if is_tracked:
                            # Git 跟踪的文件 → git rm
                            if is_dir:
                                ok, out, err = run_git(["git", "rm", "-r", del_path], cfg["repo_dir"])
                            else:
                                ok, out, err = run_git(["git", "rm", del_path], cfg["repo_dir"])
                            if ok:
                                success_count += 1
                            else:
                                fail_count += 1
                                st.write(f"❌ git rm 失败: {err}")
                        else:
                            # 未跟踪的文件 → 直接删除磁盘文件
                            try:
                                if full_path.exists():
                                    if full_path.is_dir():
                                        shutil.rmtree(full_path)
                                    else:
                                        full_path.unlink()
                                success_count += 1
                                st.write(f"✅ 已从磁盘删除（未跟踪）: {del_path}")
                            except Exception as e:
                                fail_count += 1
                                st.write(f"❌ 删除失败: {e}")

                    if success_count > 0:
                        # 检查是否有变更需要提交
                        ok_dirty, out_dirty, _ = run_git(["git", "status", "--porcelain"], cfg["repo_dir"])
                        if ok_dirty and out_dirty.strip():
                            st.write(f"📌 git commit ({success_count} 项)...")
                            run_git(["git", "commit", "-m", f"Batch delete {success_count} items"], cfg["repo_dir"])
                            st.write("📤 git push...")
                            ok, out, err = run_git(["git", "push", "origin", cfg["branch"]], cfg["repo_dir"], timeout=120)
                            if ok:
                                status.update(label=f"✅ 批量删除完成！成功 {success_count} 项", state="complete")
                                st.success(f"✅ 成功删除 {success_count} 项")
                                log_msg(f"批量删除成功: {success_count} 项")
                            else:
                                status.update(label="❌ 推送失败", state="error")
                                st.error(f"推送失败: {err}")
                        else:
                            status.update(label=f"✅ 已完成（{success_count} 项未跟踪，无需提交）", state="complete")
                            st.success(f"✅ 已删除 {success_count} 项（未跟踪文件，无需提交到远程）")
                    if fail_count > 0:
                        st.warning(f"{fail_count} 项删除失败")
                st.session_state.delete_confirm = None; st.session_state.delete_selected = []; st.rerun()
        with col_n:
            if st.button("❌ 取消", use_container_width=True):
                st.session_state.delete_confirm = None; st.rerun()


def page_open_repo():
    cfg = st.session_state.cfg
    repo_name = cfg.get("github_repo", "")
    url = f"https://github.com/{repo_name}" if repo_name else "#"
    st.markdown("## 🌐 打开 GitHub 仓库")
    st.markdown("---")
    if not repo_name:
        st.warning("⚠️ 未配置 GitHub 仓库地址，请先在设置中配置。")
        if st.button("⚙️ 前往设置"): st.session_state.page = "settings"; st.rerun()
        return

    st.markdown(
        f'<div style="text-align:center;padding:30px 20px;background:#fff;border-radius:12px;border:1px solid #e8ecf0;max-width:500px;margin:0 auto;">'
        f'<div style="font-size:56px;margin-bottom:12px;">🌐</div>'
        f'<h3 style="margin:0 0 8px 0;">{repo_name}</h3>'
        f'<p style="color:#666;font-size:14px;">点击下方按钮在浏览器中打开仓库</p>'
        f'<p style="margin:16px 0;"><a href="{url}" target="_blank" style="color:#0d6efd;font-size:15px;word-break:break-all;">{url}</a></p></div>',
        unsafe_allow_html=True)

    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        if st.button("🌐 在浏览器中打开", type="primary", use_container_width=True):
            import webbrowser; webbrowser.open(url)
            st.success(f"已尝试打开: {url}")
    with col_b2:
        if st.button("📋 复制链接", use_container_width=True):
            st.code(url, language="text"); st.info("链接已显示在上方。")
    with col_b3:
        if check_repo(cfg["repo_dir"]):
            if st.button("📊 Git 状态", use_container_width=True):
                with st.spinner("获取仓库信息..."):
                    ok, out, err = run_git(["git", "status"], cfg["repo_dir"])
                    ok2, out2, err2 = run_git(["git", "log", "--oneline", "-10"], cfg["repo_dir"])
                st.markdown("##### Git 状态"); st.code(out or "无输出", language="text")
                st.markdown("##### 最近提交"); st.code(out2 or "无提交记录", language="text")


def page_settings():
    cfg = st.session_state.cfg
    st.markdown("## ⚙️ 设置")
    st.markdown("---")

    with st.container():
        st.markdown("##### 📦 仓库配置")

        # 始终使用 session_state 中的最新输入
        gh_val = st.session_state.get("gh_repo_input", "").strip() or cfg.get("github_repo", "")
        st.text_input(
            "GitHub 仓库 (owner/repo)", value=gh_val,
            placeholder="username/repo",
            key="gh_repo_input",
            on_change=on_github_repo_change,
            help="输入仓库名后自动搜索本地路径，未找到时可选择克隆"
        )
        detected = st.session_state.get("gh_detected_path", "")
        auto_path = detected or find_local_repo(gh_val)

        # 检测结果 + 克隆选项
        if not gh_val.strip() or "/" not in gh_val:
            pass  # 还没输入完整
        elif auto_path and os.path.isdir(os.path.join(auto_path, ".git")):
            st.success(f"✅ 已检测到本地仓库: {auto_path}")
        else:
            # 未找到本地仓库 → 显示克隆选项
            repo_name = gh_val.split("/")[-1] if "/" in gh_val else gh_val
            default_clone_dir = auto_path or os.path.join(
                os.environ.get("USERPROFILE", "C:\\Users\\Default"), "Desktop", repo_name
            )

            st.warning(f"⚠️ 未找到仓库 `{gh_val}` 的本地副本")

            with st.expander("📥 克隆仓库到本地", expanded=True):
                st.markdown("选择本地目录来存放克隆的仓库：")
                st.caption(f"将在目标路径下创建 `{repo_name}` 文件夹")
                clone_path = st.text_input(
                    "克隆目标路径",
                    value=str(Path(default_clone_dir).parent),
                    key="clone_dest_path",
                    help="仓库将克隆到此目录下的 `{repo_name}` 文件夹中"
                )
                col_c1, col_c2 = st.columns([1, 3])
                with col_c1:
                    if st.button("📥 开始克隆", type="primary", use_container_width=True, key="btn_do_clone"):
                        _do_clone(gh_val, clone_path)
                with col_c2:
                    st.caption(f"将从 https://github.com/{gh_val}.git 克隆到指定目录")

        with st.form("settings_form", border=True):
            # 如果克隆成功，优先使用克隆路径
            cloned = st.session_state.get("_cloned_path", "")
            default_repo = cloned or st.session_state.get("gh_detected_path", "") or cfg.get("repo_dir", "") or find_local_repo(gh_val)
            repo_dir = st.text_input("本地仓库路径", value=default_repo, help="本地 Git 仓库的完整路径", placeholder="C:\\Users\\...\\my-repo")
            branch = st.text_input("分支名", value=cfg.get("branch", "main"), help="通常是 main 或 master")
            gh_sync = st.text_input("GitHub 仓库", value=st.session_state.get("gh_repo_input", gh_val), placeholder="username/repo", label_visibility="collapsed", disabled=True)
            st.markdown("---")
            st.markdown("##### ⚙️ 行为设置")
            delete_copy = st.toggle("上传后自动删除本地副本", value=cfg.get("delete_local_copy", True))
            submitted = st.form_submit_button("💾 保存设置", type="primary", use_container_width=True)
        if submitted:
            # 从最新输入中取值
            latest_gh = st.session_state.get("gh_repo_input", "").strip()
            cfg["repo_dir"] = repo_dir.strip(); cfg["branch"] = branch.strip()
            cfg["github_repo"] = latest_gh
            cfg["delete_local_copy"] = delete_copy
            # 清除克隆临时状态
            for k in ["_cloned_path", "gh_detected_path"]:
                st.session_state.pop(k, None)
            save_config(cfg); st.session_state.cfg = cfg
            st.success("✅ 设置已保存！"); log_msg(f"配置已保存: repo={cfg['github_repo']}, branch={cfg['branch']}")

    st.markdown("---")
    st.markdown("##### 🔍 仓库诊断")
    repo_ok = check_repo(cfg["repo_dir"]); has_remote = bool(cfg.get("github_repo"))
    diag_cols = st.columns(2)
    with diag_cols[0]:
        if not cfg.get("repo_dir"): st.markdown('<div class="badge badge-danger">❌ 未设置仓库路径</div>', unsafe_allow_html=True)
        elif repo_ok:
            st.markdown('<div class="badge badge-success">✅ 本地仓库有效</div>', unsafe_allow_html=True)
            ok, out, err = run_git(["git", "remote", "-v"], cfg["repo_dir"])
            if ok and out: st.code(out, language="text")
        else: st.markdown('<div class="badge badge-warning">⚠️ 未找到 .git 目录</div>', unsafe_allow_html=True)
    with diag_cols[1]:
        if not has_remote: st.markdown('<div class="badge badge-danger">❌ 未配置仓库地址</div>', unsafe_allow_html=True)
        else: st.markdown(f'<div class="badge badge-info">📦 {cfg["github_repo"]}</div>', unsafe_allow_html=True)

    if not repo_ok and cfg.get("repo_dir"):
        st.markdown("---")
        st.markdown("##### 🛠️ 修复工具")
        if st.button("📁 初始化为空仓库（无远程）", use_container_width=True):
            try:
                Path(cfg["repo_dir"]).mkdir(parents=True, exist_ok=True)
                run_git(["git", "init", "-b", cfg["branch"]], cfg["repo_dir"])
                if has_remote: run_git(["git", "remote", "add", "origin", f"https://github.com/{cfg['github_repo']}.git"], cfg["repo_dir"])
                st.success("✅ 空仓库初始化完成！"); st.rerun()
            except Exception as e: st.error(str(e))
        st.caption("💡 如需克隆已有仓库，请在上方「仓库配置」区域输入仓库名后操作。")

    st.markdown("---")
    with st.expander("📋 操作日志", expanded=False):
        if LOG_FILE.exists():
            with open(LOG_FILE, "r", encoding="utf-8") as f: content = f.read()
            if content.strip(): st.text(content[-3000:])
            else: st.info("暂无日志。")
        else: st.info("暂无日志。")
        if st.button("🗑️ 清空日志"):
            try: LOG_FILE.unlink(); st.success("日志已清空。")
            except Exception as e: st.error(str(e))


# ==================== 模块注册接口 ====================

class StreamlitModule:
    """所有功能模块的基类。继承此类并实现接口即可注册为新功能。"""
    @staticmethod
    def get_name() -> str: return "未命名模块"
    @staticmethod
    def get_icon() -> str: return "📦"
    @staticmethod
    def get_description() -> str: return ""
    @staticmethod
    def get_page_key() -> str: return "module_unknown"
    @staticmethod
    def render(): raise NotImplementedError


# ==================== 页面路由 ====================

PAGE_MAP = {
    "首页": page_home,
    "upload": page_upload,
    "delete": page_delete,
    "open_repo": page_open_repo,
    "settings": page_settings,
}

NAV_MAP = [
    ("首页", "house"),
    ("upload", "cloud-upload"),
    ("delete", "trash"),
    ("open_repo", "globe"),
    ("settings", "gear"),
]

NAV_LABELS = {"首页": "首页", "upload": "上传文件", "delete": "删除文件", "open_repo": "打开仓库", "settings": "设置"}


# ==================== 主入口 ====================

def main():
    st.set_page_config(page_title="GitHub 工具箱", page_icon="🧰", layout="wide", initial_sidebar_state="expanded")
    st.markdown(CSS, unsafe_allow_html=True)
    init_state()

    with st.sidebar:
            st.markdown('<div class="sidebar-mini"><div class="logo">🧰</div></div>', unsafe_allow_html=True)

            current_idx = 0
            for i, (key, _) in enumerate(NAV_MAP):
                if key == st.session_state.page: current_idx = i; break

            options = [NAV_LABELS[k] for k, _ in NAV_MAP]
            icons = [i for _, i in NAV_MAP]

            selected_label = option_menu(
                menu_title=None, options=options, icons=icons, default_index=current_idx, key="nav_menu",
                styles={
                    "container": {"padding": "0 !important", "background-color": "transparent"},
                    "icon": {"font-size": "16px", "color": "#8899aa"},
                    "nav-link": {"font-size": "15px", "text-align": "left", "font-weight": "500", "color": "#c0c0d0"},
                    "nav-link-selected": {"background-color": "rgba(13,110,253,0.25)", "color": "#fff !important"},
                })

            for key, label in NAV_LABELS.items():
                if label == selected_label and key != st.session_state.page:
                    st.session_state.page = key; st.rerun()

            st.markdown("---", unsafe_allow_html=True)
            cfg = st.session_state.cfg
            repo_ok = check_repo(cfg.get("repo_dir", "")); has_cfg = bool(cfg.get("github_repo"))
            if has_cfg and repo_ok:
                st.markdown(f'<div style="padding:4px 12px 0;"><span style="color:#4ade80;">●</span> <span style="color:#aaa;font-size:12px;">{short_path(cfg["repo_dir"], 28)}</span></div>', unsafe_allow_html=True)
            elif has_cfg:
                st.markdown(f'<div style="padding:4px 12px 0;"><span style="color:#fbbf24;">●</span> <span style="color:#aaa;font-size:12px;">仓库未就绪</span></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="padding:4px 12px 0;"><span style="color:#f87171;">●</span> <span style="color:#aaa;font-size:12px;">未配置</span></div>', unsafe_allow_html=True)

            st.markdown('<div class="sidebar-footer"><p>GitHub 工具箱 v2.0</p></div>', unsafe_allow_html=True)

    page_func = PAGE_MAP.get(st.session_state.page, page_home)
    page_func()


if __name__ == "__main__":
    main()

// ===== 应用状态 =====
const state = {
    tasks: [],
    filter: 'all',
    category: 'all',
    currentEditId: null
};

// ===== DOM 引用 =====
const DOM = {
    taskInput: document.getElementById('taskInput'),
    addBtn: document.getElementById('addBtn'),
    taskList: document.getElementById('taskListItems'),
    emptyState: document.getElementById('emptyState'),
    emptyText: document.getElementById('emptyText'),
    taskCount: document.getElementById('taskCount'),
    clearCompleted: document.getElementById('clearCompleted'),
    themeToggle: document.getElementById('themeToggle'),
    dateDisplay: document.getElementById('dateDisplay'),
    editModal: document.getElementById('editModal'),
    editInput: document.getElementById('editInput'),
    modalClose: document.getElementById('modalClose'),
    modalCancel: document.getElementById('modalCancel'),
    modalSave: document.getElementById('modalSave'),
    filterBtns: document.querySelectorAll('.filter-btn'),
    catBtns: document.querySelectorAll('.cat-btn'),
    appFooter: document.getElementById('appFooter')
};

// ===== 工具函数 =====
function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}

function formatDate(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return '今天';
    if (days === 1) return '昨天';
    if (days < 7) return `${days} 天前`;

    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${month}-${day}`;
}

function getTodayDate() {
    const now = new Date();
    const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const weekday = weekdays[now.getDay()];
    return `${year}年${month}月${day}日 ${weekday}`;
}

function getCategoryLabel(cat) {
    const labels = { personal: '个人', work: '工作', shopping: '购物', other: '其他' };
    return labels[cat] || cat;
}

// ===== 本地存储 =====
function loadTasks() {
    try {
        const data = localStorage.getItem('todolist-tasks');
        state.tasks = data ? JSON.parse(data) : [];
    } catch {
        state.tasks = [];
    }
}

function saveTasks() {
    localStorage.setItem('todolist-tasks', JSON.stringify(state.tasks));
}

// ===== 主题管理 =====
function loadTheme() {
    const theme = localStorage.getItem('todolist-theme') || 'light';
    document.documentElement.setAttribute('data-theme', theme);
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('todolist-theme', next);
    showToast(next === 'dark' ? '🌙 已切换为深色模式' : '☀️ 已切换为浅色模式');
}

// ===== Toast 通知 =====
function showToast(message) {
    let toast = document.querySelector('.toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.className = 'toast';
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(() => toast.classList.remove('show'), 2200);
}

// ===== 渲染任务 =====
function renderTasks() {
    const { filter, category } = state;

    let filtered = state.tasks;

    // 分类过滤
    if (category !== 'all') {
        filtered = filtered.filter(t => t.category === category);
    }

    // 状态过滤
    if (filter === 'active') {
        filtered = filtered.filter(t => !t.completed);
    } else if (filter === 'completed') {
        filtered = filtered.filter(t => t.completed);
    }

    if (filtered.length === 0) {
        DOM.taskList.innerHTML = '';
        DOM.emptyState.style.display = 'flex';
        const messages = {
            'all': '还没有任务，添加一个吧！',
            'active': '没有进行中的任务 🎉',
            'completed': '还没有完成的任务'
        };
        DOM.emptyText.textContent = category !== 'all'
            ? `这个分类下${messages[filter] || '还没有任务'}`
            : messages[filter] || '还没有任务，添加一个吧！';
        DOM.appFooter.style.display = state.tasks.length === 0 ? 'none' : 'flex';
        updateCount();
        return;
    }

    DOM.emptyState.style.display = 'none';
    DOM.appFooter.style.display = 'flex';

    DOM.taskList.innerHTML = filtered.map(task => `
        <li class="task-item ${task.completed ? 'completed' : ''}" data-id="${task.id}">
            <label class="task-checkbox">
                <input type="checkbox" ${task.completed ? 'checked' : ''}>
                <span class="checkmark"></span>
            </label>
            <div class="task-content">
                <div class="task-text">${escapeHtml(task.text)}</div>
                <div class="task-meta">
                    <span class="task-category cat-${task.category}">${getCategoryLabel(task.category)}</span>
                    <span class="task-date">${formatDate(task.createdAt)}</span>
                </div>
            </div>
            <div class="task-actions">
                <button class="edit-btn" title="编辑" onclick="editTask('${task.id}')">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
                        <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
                    </svg>
                </button>
                <button class="delete-btn" title="删除" onclick="deleteTask('${task.id}')">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                    </svg>
                </button>
            </div>
        </li>
    `).join('');

    updateCount();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===== 更新统计 =====
function updateCount() {
    const total = state.tasks.length;
    const completed = state.tasks.filter(t => t.completed).length;
    const active = total - completed;

    if (total === 0) {
        DOM.taskCount.textContent = '还没有任务';
    } else {
        DOM.taskCount.textContent = `共 ${total} 项 · ${active} 项进行中`;
    }

    DOM.clearCompleted.style.display = completed > 0 ? 'inline' : 'none';
}

// ===== 添加任务 =====
function addTask() {
    const text = DOM.taskInput.value.trim();
    if (!text) {
        showToast('请输入任务内容');
        DOM.taskInput.focus();
        return;
    }

    const task = {
        id: generateId(),
        text: text,
        completed: false,
        category: state.category === 'all' ? 'personal' : state.category,
        createdAt: Date.now()
    };

    state.tasks.unshift(task);
    saveTasks();
    renderTasks();
    DOM.taskInput.value = '';
    DOM.taskInput.focus();
    showToast('✅ 任务已添加');
}

// ===== 删除任务 =====
function deleteTask(id) {
    const item = document.querySelector(`[data-id="${id}"]`);
    if (item) {
        item.classList.add('removing');
        setTimeout(() => {
            state.tasks = state.tasks.filter(t => t.id !== id);
            saveTasks();
            renderTasks();
            showToast('🗑️ 任务已删除');
        }, 250);
    } else {
        state.tasks = state.tasks.filter(t => t.id !== id);
        saveTasks();
        renderTasks();
    }
}

// ===== 切换完成状态 =====
function toggleTask(id, completed) {
    const task = state.tasks.find(t => t.id === id);
    if (task) {
        task.completed = completed;
        saveTasks();
        renderTasks();
    }
}

// ===== 编辑任务 =====
function editTask(id) {
    const task = state.tasks.find(t => t.id === id);
    if (!task) return;

    state.currentEditId = id;
    DOM.editInput.value = task.text;
    DOM.editModal.classList.add('active');
    setTimeout(() => DOM.editInput.focus(), 100);
}

function saveEdit() {
    const text = DOM.editInput.value.trim();
    if (!text) {
        showToast('任务内容不能为空');
        return;
    }

    const task = state.tasks.find(t => t.id === state.currentEditId);
    if (task) {
        task.text = text;
        saveTasks();
        renderTasks();
        showToast('✏️ 任务已更新');
    }

    closeEditModal();
}

function closeEditModal() {
    DOM.editModal.classList.remove('active');
    state.currentEditId = null;
    DOM.editInput.value = '';
}

// ===== 清除已完成 =====
function clearCompleted() {
    const completed = state.tasks.filter(t => t.completed);
    if (completed.length === 0) {
        showToast('没有已完成的任务');
        return;
    }

    state.tasks = state.tasks.filter(t => !t.completed);
    saveTasks();
    renderTasks();
    showToast(`🗑️ 已清除 ${completed.length} 项已完成任务`);
}

// ===== 切换过滤器 =====
function setFilter(filter) {
    state.filter = filter;
    DOM.filterBtns.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.filter === filter);
    });
    renderTasks();
}

// ===== 切换分类 =====
function setCategory(category) {
    state.category = category;
    DOM.catBtns.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.category === category);
    });
    renderTasks();
}

// ===== 事件绑定 =====
function initEvents() {
    // 添加任务
    DOM.addBtn.addEventListener('click', addTask);
    DOM.taskInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') addTask();
    });

    // 任务列表事件委托（复选框切换）
    DOM.taskList.addEventListener('change', (e) => {
        if (e.target.type === 'checkbox') {
            const item = e.target.closest('.task-item');
            if (item) {
                toggleTask(item.dataset.id, e.target.checked);
            }
        }
    });

    // 点击任务文本快速编辑
    DOM.taskList.addEventListener('dblclick', (e) => {
        const textEl = e.target.closest('.task-text');
        if (textEl) {
            const item = textEl.closest('.task-item');
            if (item) editTask(item.dataset.id);
        }
    });

    // 过滤器
    DOM.filterBtns.forEach(btn => {
        btn.addEventListener('click', () => setFilter(btn.dataset.filter));
    });

    // 分类
    DOM.catBtns.forEach(btn => {
        btn.addEventListener('click', () => setCategory(btn.dataset.category));
    });

    // 主题切换
    DOM.themeToggle.addEventListener('click', toggleTheme);

    // 清除已完成
    DOM.clearCompleted.addEventListener('click', clearCompleted);

    // 编辑弹窗
    DOM.modalClose.addEventListener('click', closeEditModal);
    DOM.modalCancel.addEventListener('click', closeEditModal);
    DOM.modalSave.addEventListener('click', saveEdit);
    DOM.editInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') saveEdit();
        if (e.key === 'Escape') closeEditModal();
    });

    // 点击遮罩关闭弹窗
    DOM.editModal.addEventListener('click', (e) => {
        if (e.target === DOM.editModal) closeEditModal();
    });

    // 全局键盘快捷键
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && DOM.editModal.classList.contains('active')) {
            closeEditModal();
        }
        // Ctrl+N 新建任务
        if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
            e.preventDefault();
            DOM.taskInput.focus();
        }
    });
}

// ===== 初始化 =====
function init() {
    loadTheme();
    loadTasks();
    DOM.dateDisplay.textContent = getTodayDate();
    renderTasks();
    initEvents();

    // 每5秒更新日期
    setInterval(() => {
        DOM.dateDisplay.textContent = getTodayDate();
    }, 5000);
}

// 启动应用
init();

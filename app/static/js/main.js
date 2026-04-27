// app/static/js/main.js

document.addEventListener('DOMContentLoaded', function() {
    // 自动隐藏 flash 消息
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.transition = 'opacity 0.5s ease';
            message.style.opacity = '0';
            setTimeout(() => {
                if (message.parentNode) {
                    message.parentNode.removeChild(message);
                }
            }, 500);
        }, 5000);
    });

    // 表单验证增强
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = this.querySelector('button[type="submit"], input[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = '提交中...';
            }
        });
    });

    // 文章内容图片懒加载
    const postImages = document.querySelectorAll('.post-content img');
    postImages.forEach(img => {
        img.loading = 'lazy';
    });

    // 评论表单增强
    const commentForms = document.querySelectorAll('.comment-form');
    commentForms.forEach(form => {
        const textarea = form.querySelector('textarea');
        if (textarea) {
            // 自动调整文本域高度
            textarea.addEventListener('input', function() {
                this.style.height = 'auto';
                this.style.height = (this.scrollHeight) + 'px';
            });
        }
    });

    // 删除确认
    const deleteForms = document.querySelectorAll('form[onsubmit*="confirm"]');
    deleteForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const confirmMessage = this.getAttribute('onsubmit').match(/return confirm\('([^']+)'\)/);
            if (confirmMessage && !confirm(confirmMessage[1])) {
                e.preventDefault();
            }
        });
    });

    // 搜索框增强
    const searchForms = document.querySelectorAll('form[action*="search"]');
    searchForms.forEach(form => {
        const searchInput = form.querySelector('input[type="text"]');
        if (searchInput) {
            searchInput.addEventListener('focus', function() {
                this.select();
            });
        }
    });

    // 分页改进
    const paginationLinks = document.querySelectorAll('.pagination a');
    paginationLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            this.style.opacity = '0.7';
        });
    });
});

// 工具函数
const BlogUtils = {
    // 格式化日期
    formatDate: function(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    // 截断文本
    truncateText: function(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substr(0, maxLength) + '...';
    },

    // 防抖函数
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};

// Markdown 预览功能（如果使用 Markdown 编辑器）
if (typeof marked !== 'undefined') {
    const markdownEditors = document.querySelectorAll('.markdown-editor');
    markdownEditors.forEach(editor => {
        const textarea = editor.querySelector('textarea');
        const preview = editor.querySelector('.markdown-preview');

        if (textarea && preview) {
            textarea.addEventListener('input', BlogUtils.debounce(function() {
                preview.innerHTML = marked.parse(this.value);
            }, 300));
        }
    });
}
/**
 * Markdown Editor with Image Upload Support
 *
 * Features:
 * - Edit/Preview toggle
 * - Drag & Drop image upload
 * - Paste image from clipboard
 * - Auto-insert Markdown image syntax
 *
 * Usage:
 *   <div class="markdown-editor" data-upload-url="/api/upload/image">
 *     <textarea name="content">...</textarea>
 *   </div>
 *   <script src="/static/js/markdown-editor.js"></script>
 */

(function() {
    'use strict';

    // Initialize all markdown editors on the page or within a container
    function initMarkdownEditors(container) {
        // Handle being called as event handler (container would be Event object)
        const root = (container && container.querySelectorAll) ? container : document;
        root.querySelectorAll('.markdown-editor').forEach(initEditor);
    }

    function initEditor(container) {
        // Prevent double initialization
        if (container.dataset.markdownEditorInitialized) return;
        container.dataset.markdownEditorInitialized = 'true';

        const textarea = container.querySelector('textarea');
        if (!textarea) return;

        const uploadUrl = container.dataset.uploadUrl || '/api/upload/image';
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content ||
                          document.querySelector('input[name="csrf_token"]')?.value;

        // Create toolbar if not exists
        let toolbar = container.querySelector('.markdown-editor-toolbar');
        if (!toolbar) {
            toolbar = createToolbar();
            container.insertBefore(toolbar, textarea);
        }

        // Create preview container if not exists
        let preview = container.querySelector('.markdown-preview');
        if (!preview) {
            preview = document.createElement('div');
            preview.className = 'markdown-preview d-none';
            textarea.parentNode.insertBefore(preview, textarea.nextSibling);
        }

        // Create dropzone overlay
        let dropzone = container.querySelector('.markdown-dropzone');
        if (!dropzone) {
            dropzone = document.createElement('div');
            dropzone.className = 'markdown-dropzone d-none';
            dropzone.innerHTML = '<i class="ti ti-upload"></i> Bild hier ablegen';
            container.appendChild(dropzone);
        }

        // State
        let isPreviewMode = false;

        // Toolbar button handlers
        toolbar.querySelector('[data-mode="edit"]').addEventListener('click', () => {
            setMode('edit');
        });

        toolbar.querySelector('[data-mode="preview"]').addEventListener('click', () => {
            setMode('preview');
        });

        function setMode(mode) {
            isPreviewMode = mode === 'preview';

            // Update buttons
            toolbar.querySelectorAll('button').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.mode === mode);
            });

            // Toggle visibility
            textarea.classList.toggle('d-none', isPreviewMode);
            preview.classList.toggle('d-none', !isPreviewMode);

            // Render preview
            if (isPreviewMode) {
                renderPreview();
            }
        }

        function renderPreview() {
            const content = textarea.value;

            // Use marked.js if available, otherwise simple rendering
            if (typeof marked !== 'undefined') {
                preview.innerHTML = marked.parse(content);
            } else {
                // Simple fallback: convert basic markdown
                preview.innerHTML = simpleMarkdownRender(content);
            }

            // Make images clickable (open in new tab)
            preview.querySelectorAll('img').forEach(img => {
                img.style.cursor = 'pointer';
                img.style.maxWidth = '100%';
                img.addEventListener('click', () => {
                    window.open(img.src, '_blank');
                });
            });
        }

        function simpleMarkdownRender(text) {
            // Very basic markdown rendering as fallback
            return text
                // Escape HTML
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                // Images: ![alt](url)
                .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" style="max-width:100%">')
                // Links: [text](url)
                .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
                // Bold: **text**
                .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
                // Italic: *text*
                .replace(/\*([^*]+)\*/g, '<em>$1</em>')
                // Code: `code`
                .replace(/`([^`]+)`/g, '<code>$1</code>')
                // Line breaks
                .replace(/\n/g, '<br>');
        }

        // Drag & Drop handlers
        container.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (hasImageFile(e.dataTransfer)) {
                dropzone.classList.remove('d-none');
            }
        });

        container.addEventListener('dragleave', (e) => {
            e.preventDefault();
            e.stopPropagation();
            // Only hide if leaving the container entirely
            if (!container.contains(e.relatedTarget)) {
                dropzone.classList.add('d-none');
            }
        });

        container.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('d-none');

            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleImageUpload(files[0]);
            }
        });

        // Paste handler
        textarea.addEventListener('paste', (e) => {
            const items = e.clipboardData?.items;
            if (!items) return;

            for (const item of items) {
                if (item.type.startsWith('image/')) {
                    e.preventDefault();
                    const file = item.getAsFile();
                    if (file) {
                        handleImageUpload(file);
                    }
                    break;
                }
            }
        });

        function hasImageFile(dataTransfer) {
            if (dataTransfer.types.includes('Files')) {
                for (const item of dataTransfer.items) {
                    if (item.type.startsWith('image/')) {
                        return true;
                    }
                }
            }
            return false;
        }

        async function handleImageUpload(file) {
            // Validate file type
            if (!file.type.startsWith('image/')) {
                showError('Nur Bilder können hochgeladen werden');
                return;
            }

            // Validate file size (5 MB)
            const maxSize = 5 * 1024 * 1024;
            if (file.size > maxSize) {
                showError('Datei zu groß. Maximum: 5 MB');
                return;
            }

            // Show loading state
            const loadingText = `![Bild wird hochgeladen...](loading)`;
            insertAtCursor(loadingText);
            const loadingStart = textarea.value.lastIndexOf(loadingText);

            try {
                const formData = new FormData();
                formData.append('file', file);

                const response = await fetch(uploadUrl, {
                    method: 'POST',
                    headers: csrfToken ? { 'X-CSRFToken': csrfToken } : {},
                    body: formData
                });

                const result = await response.json();

                if (result.success) {
                    // Replace loading text with actual markdown
                    const currentValue = textarea.value;
                    textarea.value = currentValue.substring(0, loadingStart) +
                                     result.markdown +
                                     currentValue.substring(loadingStart + loadingText.length);

                    // Trigger change event
                    textarea.dispatchEvent(new Event('change', { bubbles: true }));
                } else {
                    // Remove loading text and show error
                    removeLoadingText(loadingStart, loadingText.length);
                    showError(result.error || 'Upload fehlgeschlagen');
                }
            } catch (error) {
                removeLoadingText(loadingStart, loadingText.length);
                showError('Upload fehlgeschlagen: ' + error.message);
            }
        }

        function insertAtCursor(text) {
            const start = textarea.selectionStart;
            const end = textarea.selectionEnd;
            const value = textarea.value;

            textarea.value = value.substring(0, start) + text + value.substring(end);
            textarea.selectionStart = textarea.selectionEnd = start + text.length;
            textarea.focus();
        }

        function removeLoadingText(start, length) {
            const value = textarea.value;
            textarea.value = value.substring(0, start) + value.substring(start + length);
        }

        function showError(message) {
            // Use Bootstrap toast if available
            if (typeof bootstrap !== 'undefined' && document.querySelector('.toast-container')) {
                const toastEl = document.createElement('div');
                toastEl.className = 'toast align-items-center text-white bg-danger border-0';
                toastEl.setAttribute('role', 'alert');
                toastEl.innerHTML = `
                    <div class="d-flex">
                        <div class="toast-body">${message}</div>
                        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                    </div>
                `;
                document.querySelector('.toast-container').appendChild(toastEl);
                const toast = new bootstrap.Toast(toastEl);
                toast.show();
                toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
            } else {
                alert(message);
            }
        }
    }

    function createToolbar() {
        const toolbar = document.createElement('div');
        toolbar.className = 'markdown-editor-toolbar mb-2';
        toolbar.innerHTML = `
            <div class="btn-group btn-group-sm" role="group">
                <button type="button" class="btn btn-outline-secondary active" data-mode="edit">
                    <i class="ti ti-pencil"></i> Bearbeiten
                </button>
                <button type="button" class="btn btn-outline-secondary" data-mode="preview">
                    <i class="ti ti-eye"></i> Preview
                </button>
            </div>
            <small class="text-muted ms-2">
                <i class="ti ti-photo"></i> Bilder: Drag & Drop oder Einfügen (Strg+V)
            </small>
        `;
        return toolbar;
    }

    // Auto-initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initMarkdownEditors);
    } else {
        initMarkdownEditors();
    }

    // Export for manual initialization
    window.initMarkdownEditors = initMarkdownEditors;
    window.initMarkdownEditor = initEditor;
})();

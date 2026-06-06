// ─── Chatbot ──────────────────────────────────────────────────────────────
function toggleChat() {
  const panel = document.getElementById('chatbot-panel');
  if (panel) panel.classList.toggle('hidden');
}

async function sendChat() {
  const input = document.getElementById('chatbot-input');
  const messages = document.getElementById('chatbot-messages');
  const msg = input.value.trim();
  if (!msg) return;

  // User bubble
  appendBubble(messages, msg, 'user');
  input.value = '';

  // Typing indicator
  const typing = appendTyping(messages);

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg })
    });
    const data = await res.json();
    typing.remove();
    appendBubble(messages, data.reply, 'bot');
  } catch {
    typing.remove();
    appendBubble(messages, '⚠️ Connection error. Please try again.', 'bot');
  }
}

function appendBubble(container, text, role) {
  const div = document.createElement('div');
  div.className = `chat-msg ${role}`;
  // Convert **bold** markdown and newlines
  const formatted = text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>');
  div.innerHTML = `<div class="chat-bubble">${formatted}</div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function appendTyping(container) {
  const div = document.createElement('div');
  div.className = 'chat-msg bot';
  div.innerHTML = `<div class="chat-bubble"><div class="typing-dots"><span></span><span></span><span></span></div></div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div;
}

// Allow Enter key in chatbot input
document.addEventListener('DOMContentLoaded', () => {
  const inp = document.getElementById('chatbot-input');
  if (inp) {
    inp.addEventListener('keydown', e => {
      if (e.key === 'Enter') sendChat();
    });
  }
});

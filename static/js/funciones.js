document.addEventListener('DOMContentLoaded', () => {
  // Cierra avisos del servidor.
  document.querySelectorAll('.flash-close').forEach(button => button.addEventListener('click', () => button.closest('.flash').remove()));

  // Carrusel destacado: botones, indicadores, autoplay y pausa.
  document.querySelectorAll('[data-slider]').forEach(slider => {
    const slides = [...slider.querySelectorAll('[data-slide]')];
    const dots = [...slider.querySelectorAll('[data-dot]')];
    const counter = slider.querySelector('[data-counter]');
    const pauseButton = slider.querySelector('[data-pause]');
    if (!slides.length) return;
    let current = 0, paused = false, timer;
    const show = index => {
      current = (index + slides.length) % slides.length;
      slides.forEach((slide, i) => slide.classList.toggle('is-active', i === current));
      dots.forEach((dot, i) => dot.classList.toggle('active', i === current));
      if (counter) counter.textContent = `${String(current + 1).padStart(2,'0')} / ${String(slides.length).padStart(2,'0')}`;
    };
    const restart = () => { clearInterval(timer); if (!paused && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) timer = setInterval(() => show(current + 1), 6500); };
    slider.querySelector('[data-prev]')?.addEventListener('click', () => { show(current - 1); restart(); });
    slider.querySelector('[data-next]')?.addEventListener('click', () => { show(current + 1); restart(); });
    dots.forEach(dot => dot.addEventListener('click', () => { show(Number(dot.dataset.dot)); restart(); }));
    pauseButton?.addEventListener('click', () => { paused = !paused; pauseButton.textContent = paused ? '▶' : 'Ⅱ'; pauseButton.setAttribute('aria-label', paused ? 'Reanudar carrusel' : 'Pausar carrusel'); restart(); });
    slider.addEventListener('mouseenter', () => clearInterval(timer));
    slider.addEventListener('mouseleave', restart);
    show(0); restart();
  });

  // Alterna formulario de inicio de sesión y registro.
  const tabs = [...document.querySelectorAll('[data-auth-tab]')];
  const forms = [...document.querySelectorAll('[data-auth-form]')];
  tabs.forEach(tab => tab.addEventListener('click', () => {
    tabs.forEach(item => item.classList.toggle('active', item === tab));
    forms.forEach(form => form.classList.toggle('hidden', form.dataset.authForm !== tab.dataset.authTab));
  }));

  // Confirmación antes de eliminar usuarios desde administración.
  document.querySelectorAll('form[data-confirm]').forEach(form => form.addEventListener('submit', event => {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  }));

  // Atajo de teclado: "/" enfoca el buscador sin interferir con formularios.
  document.addEventListener('keydown', event => {
    if (event.key === '/' && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)) {
      const search = document.querySelector('.search-box input');
      if (search) { event.preventDefault(); search.focus(); }
    }
  });

  // Asistente Pixel para orientar a los visitantes sobre los juegos de SSRCM.
  const chatToggle = document.getElementById('pixel-chat-toggle');
  const chatPanel = document.getElementById('pixel-chat-panel');
  const chatClose = document.getElementById('pixel-chat-close');
  const chatForm = document.getElementById('pixel-chat-form');
  const chatInput = document.getElementById('pixel-chat-input');
  const chatMessages = document.getElementById('pixel-chat-messages');

  const openPixelChat = open => {
    if (!chatPanel || !chatToggle) return;
    chatPanel.hidden = !open;
    chatToggle.setAttribute('aria-expanded', String(open));
    if (open) chatInput?.focus();
  };
  chatToggle?.addEventListener('click', () => openPixelChat(chatPanel.hidden));
  chatClose?.addEventListener('click', () => openPixelChat(false));

  const addPixelMessage = (message, sender) => {
    const bubble = document.createElement('div');
    bubble.className = `pixel-message ${sender === 'user' ? 'user-message' : 'bot-message'}`;
    bubble.textContent = message;
    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return bubble;
  };

  const askPixel = async message => {
    addPixelMessage(message, 'user');
    const waiting = addPixelMessage('Pixel está pensando…', 'bot');
    chatInput.disabled = true;
    const sendButton = chatForm?.querySelector('button[type="submit"]');
    if (sendButton) sendButton.disabled = true;
    try {
      const response = await fetch('/api/asistente', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
      });
      const data = await response.json();
      waiting.textContent = data.reply || 'No pude responder ahora. Inténtalo otra vez.';
    } catch (error) {
      waiting.textContent = 'No pude conectarme en este momento. Comprueba que la página esté funcionando e inténtalo de nuevo.';
    } finally {
      chatInput.disabled = false;
      if (sendButton) sendButton.disabled = false;
      chatInput.focus();
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
  };

  chatForm?.addEventListener('submit', event => {
    event.preventDefault();
    const message = chatInput.value.trim();
    if (!message) return;
    chatInput.value = '';
    askPixel(message);
  });
  document.querySelectorAll('[data-pixel-prompt]').forEach(button => {
    button.addEventListener('click', () => {
      openPixelChat(true);
      askPixel(button.dataset.pixelPrompt);
    });
  });

});

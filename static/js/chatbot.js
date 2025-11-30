document.addEventListener("DOMContentLoaded", function() {
  const sendBtn = document.getElementById("chat-send");
  const input = document.getElementById("chat-input");
  const messages = document.getElementById("chat-messages");

  function appendMsg(author, text) {
    const el = document.createElement("div");
    el.innerHTML = `<div class="small"><strong>${author}:</strong> ${text}</div>`;
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
  }

  sendBtn.addEventListener("click", async () => {
    const prompt = input.value.trim();
    if (!prompt) return;
    appendMsg("You", prompt);
    input.value = "";
    appendMsg("AI", "Thinking...");
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt })
      });
      const data = await res.json();
      // remove last "Thinking..." element
      messages.lastChild.remove();
      if (data.reply) appendMsg("AI", data.reply);
      else appendMsg("AI", "No reply.");
    } catch (err) {
      messages.lastChild.remove();
      appendMsg("AI", "Error contacting AI.");
    }
  });

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendBtn.click();
  });
});

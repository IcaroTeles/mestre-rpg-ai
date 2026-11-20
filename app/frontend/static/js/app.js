async function checkHealth() {
    const serverStatus = document.getElementById("server-status");
    const ollamaStatus = document.getElementById("ollama-status");

    try {
        const response = await fetch("/api/health");
        if (!response.ok) throw new Error("Falha no servidor");
        await response.json();
        serverStatus.textContent = "Online";
        serverStatus.classList.add("online");
    } catch (error) {
        serverStatus.textContent = "Indisponivel";
        serverStatus.classList.add("offline");
    }

    try {
        const response = await fetch("/api/health/ollama");
        const data = await response.json();
        if (data.ollama.available && data.ollama.model_installed) {
            ollamaStatus.textContent = "Online";
            ollamaStatus.classList.add("online");
        } else {
            ollamaStatus.textContent = data.ollama.model_installed ? "Indisponivel" : "Modelo ausente";
            ollamaStatus.classList.add("offline");
        }
    } catch (error) {
        ollamaStatus.textContent = "Indisponivel";
        ollamaStatus.classList.add("offline");
    }
}

checkHealth();

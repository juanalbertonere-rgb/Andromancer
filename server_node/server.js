const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const { Telegraf } = require('telegraf');
const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');

// --- 1. CONFIGURACIÓN: LEER TOKEN DE SETTINGS.PY ---
const settingsPath = path.join(__dirname, '../settings.py');
let TELEGRAM_TOKEN = '';

try {
    const settingsContent = fs.readFileSync(settingsPath, 'utf8');
    // Regex para buscar TELEGRAM_BOT_TOKEN = "..." o '...'
    const tokenMatch = settingsContent.match(/TELEGRAM_BOT_TOKEN\s*=\s*["']([^"']+)["']/);
    if (tokenMatch && tokenMatch[1] && !tokenMatch[1].includes('xxxxx')) {
        TELEGRAM_TOKEN = tokenMatch[1];
    } else {
        throw new Error("Token no válido o contiene 'xxxxx'");
    }
} catch (err) {
    console.error("❌ ERROR CRÍTICO: No se pudo leer el Token de settings.py");
    console.error("Asegúrate de haber puesto tu token real en el archivo settings.py");
    process.exit(1);
}

// --- 2. INICIALIZACIÓN DE SERVIDORES ---
const app = express();
const server = http.createServer(app);
const io = new Server(server);
const bot = new Telegraf(TELEGRAM_TOKEN);

app.use(express.static('public'));

// --- 3. LÓGICA DE EJECUCIÓN (EL PUENTE) ---
function runAndromancer(comando, source, ctx = null) {
    const pythonPath = path.join(__dirname, '../andromancer.py');
    
    // Notificar a la web que el usuario envió algo
    io.emit('chat message', { role: 'user', text: comando, source: source });

    // Llamar a Python pasando el comando como argumento
    exec(`python3 "${pythonPath}" "${comando}"`, (error, stdout, stderr) => {
        let response = "";
        
        if (error) {
            response = `❌ Error de ejecución: ${error.message}`;
        } else {
            // Limpiamos la salida para mostrar solo lo relevante
            response = stdout || "✅ Comando procesado con éxito.";
        }

        // Enviar respuesta a la web
        io.emit('chat message', { role: 'assistant', text: response });

        // Si vino de Telegram, responder por Telegram también
        if (source === 'telegram' && ctx) {
            ctx.reply(response.slice(0, 4000)); // Límite de caracteres de Telegram
        }
    });
}

// --- 4. EVENTOS DE TELEGRAM ---
bot.on('text', (ctx) => {
    const msg = ctx.message.text;
    if (msg.toLowerCase().startsWith('do ')) {
        runAndromancer(msg, 'telegram', ctx);
    }
});

bot.launch().then(() => {
    console.log('✅ Bot de Telegram conectado correctamente.');
}).catch(err => {
    console.error('❌ Error al lanzar el bot:', err);
});

// --- 5. EVENTOS DE LA WEB (SOCKET) ---
io.on('connection', (socket) => {
    console.log('🌐 Cliente conectado al Dashboard Web');
    
    socket.on('chat message', (msg) => {
        // Ejecutar directamente lo que se escriba en la web
        runAndromancer(msg, 'web');
    });
});

// --- 6. ARRANQUE ---
const PORT = 3000;
server.listen(PORT, () => {
    console.log(`🚀 DASHBOARD PROFESIONAL ACTIVO`);
    console.log(`📍 URL: http://localhost:${PORT}`);
    console.log(`🤖 Bot vinculado: ${TELEGRAM_TOKEN.split(':')[0]}`);
});

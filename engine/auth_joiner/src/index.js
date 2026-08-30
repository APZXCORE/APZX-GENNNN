// APZX Auth Joiner
const express = require('express')
const app = express()
const port = 3001
const config = require("../../../config.json");
const { web, bot, data } = config.auth_joiner;

const { Client, GatewayIntentBits, ActivityType } = require('discord.js');
const client = new Client({ intents: [GatewayIntentBits.Guilds] });

const axios = require('axios').default;

const { HttpsProxyAgent } = require('https-proxy-agent');
const fs = require('fs');
const path = require('path');

// Load proxies from the local directory
let proxies = [];
try {
  const proxyPath = path.join(__dirname, '../../../input/proxies.txt');
  proxies = fs.readFileSync(proxyPath, 'utf8').split(/\r?\n/).filter(p => p.trim() !== '');
} catch (e) {
  console.log('[APZX] Could not load proxies.txt. Will run without proxies.');
}

function getRandomProxyAgent() {
  if (proxies.length === 0) return undefined;
  let p = proxies[Math.floor(Math.random() * proxies.length)];
  // Handle user:pass@ip:port vs ip:port
  if (!p.startsWith('http')) {
    if (p.includes('@')) {
       p = 'http://' + p;
    } else {
       // if it's user:pass:ip:port convert to user:pass@ip:port
       const parts = p.split(':');
       if(parts.length === 4) {
           p = `http://${parts[0]}:${parts[1]}@${parts[2]}:${parts[3]}`;
       } else {
           p = 'http://' + p;
       }
    }
  }
  return new HttpsProxyAgent(p);
}

app.get('/', async (req, res) => {
  try {
    let query = req.query.code
    if (!query) return res.status(404).send("Not Found Code")

    const agent = getRandomProxyAgent();

    const tokenResponseData = await axios({
      method: 'POST',
      url: 'https://discord.com/api/oauth2/token',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      data: new URLSearchParams({
        client_id: bot.id,
        client_secret: bot.secret,
        code: query,
        grant_type: 'authorization_code',
        redirect_uri: `${web.url}`,
        scope: 'identify',
      }).toString(),
      httpsAgent: agent
    }).then(x => x.data);

    if (!tokenResponseData) return res.status(404).send("Not Found Code")

    const userResponseData = await axios({
      method: 'GET',
      url: 'https://discord.com/api/users/@me',
      headers: {
        authorization: `${tokenResponseData.token_type} ${tokenResponseData.access_token}`
      },
      httpsAgent: agent
    }).then(x => x.data);

    if (!userResponseData) return res.status(404).send("Not Found Code")

    let guild = client.guilds.cache.get(data.guildId)
    if (!guild) return res.status(404).json({ joined: false, message: "Not Found Guild" })

    guild.members.add(userResponseData.id, { accessToken: tokenResponseData.access_token }).then(() => {
      res.status(200).json({ joined: true, message: `[APZX] ${userResponseData.username}#${userResponseData.discriminator} (${userResponseData.id}) joined the server!` })
    }).catch(err => {
      res.status(404).json({ joined: false, message: `[APZX] ${userResponseData.username}#${userResponseData.discriminator} (${userResponseData.id}) Failed join the server! - ` + err.message })
    })
  } catch (err) {
    res.status(404).send("Not Found Code")
  }
})

const P = "\x1b[38;2;121;3;255m";
const C = "\x1b[38;2;0;255;220m";
const R = "\x1b[0m";

app.listen(port, () => {
  client.login(bot.token)
  client.on('ready', () => {
    console.log(`  ${C}[APZX] ${client.user.tag} proxy bridge is connected!${R}`);
    setTimeout(() => {
      require('./main.js')
    }, 3000);
  });
})
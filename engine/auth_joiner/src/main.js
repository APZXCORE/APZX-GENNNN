// APZX Auth Joiner
const fs = require("fs");
const fetch = require("node-fetch");
const config = require("../../../config.json").auth_joiner;
const path = require("path");
const { HttpsProxyAgent } = require('https-proxy-agent');

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
  if (!p.startsWith('http')) {
    if (p.includes('@')) {
       p = 'http://' + p;
    } else {
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

const P = "\x1b[38;2;121;3;255m";
const C = "\x1b[38;2;0;255;220m";
const G = "\x1b[38;2;0;255;136m";
const Y = "\x1b[38;2;255;200;0m";
const D = "\x1b[38;2;100;100;110m";
const RD = "\x1b[38;2;255;50;80m";
const R = "\x1b[0m";

let i = 0;

(async () => {
  let filePath = path.join(__dirname, '../../../input/tokens.txt');
  let cleanedFilePath = [];
  try {
     cleanedFilePath = fs.readFileSync(filePath, 'utf8').split(/\r?\n/);
  } catch(e) {
     console.log(`  ${RD}[!] No tokens found in output/email_verified.txt or input/tokens.txt!${R}`);
     return;
  }
  const CHUNK_SIZE = 50; // Execute 50 requests concurrently
  for (let c = 0; c < cleanedFilePath.length; c += CHUNK_SIZE) {
    const chunk = cleanedFilePath.slice(c, c + CHUNK_SIZE);
    
    await Promise.all(chunk.map(async (rawToken) => {
      if (!rawToken) return;
      const parts = rawToken.replace(/"/g, '').split(':');
      const token = parts.length >= 3 ? parts[2] : parts[0];
      const shortToken = token.length > 20 ? token.substring(0, 15) : token;
      
      try {
        const agent = getRandomProxyAgent();
        let response = await fetch(`https://discord.com/api/oauth2/authorize?client_id=${config.bot.id}&redirect_uri=http%3A%2F%2Flocalhost%3A3001&response_type=code&scope=identify%20email%20guilds.join`, { 
          "headers": { "authorization": token, "content-type": "application/json" }, 
          "body": "{\"permissions\":\"0\",\"authorize\":true}", 
          "method": "POST",
          "agent": agent
        });
        
        if (response.status === 429) {
          console.log(`  ${Y}[Rate Limit] OAuth Authorize rate limited for token ${shortToken}...${R}`);
          return;
        } else if (response.status === 401 || response.status === 403) {
          // Check for locked state explicitly via guilds
          let isLocked = false;
          try {
            let chk = await fetch("https://discord.com/api/v9/users/@me/guilds", {
                "headers": { "authorization": token },
                "agent": agent
            });
            let txt = await chk.text();
            if (chk.status === 401 || chk.status === 403) {
                if (txt.includes("verify your account") || txt.includes("suspicious") || txt.includes("40002")) {
                    isLocked = true;
                }
            }
          } catch(e) {}
          
          if (isLocked) {
             console.log(`  ${Y}Locked: ${shortToken}...${R}`);
          } else {
             console.log(`  ${RD}Invalid: ${shortToken}...${R}`);
          }
          return;
        }

        let data = await response.json();
        
        if (data.location) {
          await fetch(data.location).then(x => x.json()).then(x => {
            if (x.joined) {
              i++;
              console.log(`  ${G}✓ Joined [${i}] - ${x.message}${R}`);
            } else {
              console.log(`  ${RD}✗ Failed - ${x.message}${R}`);
            }
          }).catch(err => { 
            console.log(`  ${RD}✗ Local Server Error: ${err.message}${R}`);
          });
        } else {
            console.log(`  ${D}? No location redirect for token ${shortToken}...${R}`);
        }
      } catch (err) { 
        console.log(`  ${RD}✗ Fetch Error: ${err.message}${R}`);
      }
    }));
  }
  console.log(`\n  ${P}┌──────────────────────────────────────────┐${R}`);
  console.log(`  ${P}│${R}  ${G}✓ Finished submitting all tokens!${R}         ${P}│${R}`);
  console.log(`  ${P}└──────────────────────────────────────────┘${R}\n`);
})();
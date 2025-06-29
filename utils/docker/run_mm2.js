import init, { mm2_main, LogLevel } from './kdf/mm2lib.js';
import fs from 'fs';

(async () => {
  await init();
  const confPath = process.env.MM2_CONFIG || '/home/node/.kdf/MM2.json';
  const rawConf  = fs.readFileSync(confPath, 'utf8');
  const conf     = JSON.parse(rawConf);
  const params   = { conf, log_level: LogLevel.Info };
  // Simple log handler that prints everything to stdout.
  function handleLog(level, line) {
    console.log(`[${level}] ${line}`);
  }
  mm2_main(params, handleLog);
  // Keep the container running.
  process.stdin.resume();
})(); 
const fs = require("fs");
const path = require("path");

function walkDir(dirPath, callback) {
  fs.readdirSync(dirPath).forEach((file) => {
    const filePath = path.join(dirPath, file);
    const stat = fs.statSync(filePath);
    if (stat.isDirectory()) {
      walkDir(filePath, callback);
    } else {
      callback(filePath);
    }
  });
}

const fileNames = [];
const getFileNames = (filepath) => {
  fileNames.push(filepath);
};

walkDir("./src/pages", getFileNames);

const mapDirObj = {
  "/antara/api/": "/basic-docs/antara/antara-api/",
  "/antara/setup/": "/basic-docs/antara/antara-setup/",
  "/antara/tutorials/": "/basic-docs/antara/antara-tutorials/",
  "/komodo-defi-framework/changelog/": "/basic-docs/atomicdex/changelog/",
  "/komodo-defi-framework/api/legacy/": "/basic-docs/atomicdex-api-legacy/",
  "/komodo-defi-framework/api/v20/": "/basic-docs/atomicdex-api-20/",
  "/komodo-defi-framework/api/v20-dev/": "/basic-docs/atomicdex-api-20-dev/",
  "/komodo-defi-framework/mobile/": "/basic-docs/atomicdex/atomicdex-beta/",
  "/komodo-defi-framework/setup/": "/basic-docs/atomicdex/atomicdex-setup/",
  "/komodo-defi-framework/tutorials/": "/basic-docs/atomicdex/atomicdex-tutorials/",
  "/historical/cc-jl/": "/cc-jl/",
  "/historical/whitepaper/": "/whitepaper/",
  "/smart-chains/api/": "/basic-docs/smart-chains/smart-chain-api/",
  "/smart-chains/changelog/": "/basic-docs/smart-chains/changelog/",
  "/smart-chains/setup/": "/basic-docs/smart-chains/smart-chain-setup/",
  "/smart-chains/tutorials/": "/basic-docs/smart-chains/smart-chain-tutorials/",
  "/start-here/": "/basic-docs/start-here/",
  "/komodo/": "/komodo/",
  "/notary/": "/notary/",
  "/qa/": "/qa/",
  "/resources/": "/resources/",
};

let pathObj = {};
fileNames.forEach((filePath) => {
  for (const newPath in mapDirObj) {
    if (filePath.includes("src/pages" + newPath)) {
      pathObj[
        filePath
          .replace(newPath, mapDirObj[newPath])
          .replace("src/pages", "")
          .replace("index.mdx", "")
          .slice(0, -1) + ".html"
      ] = filePath.replace("src/pages", "").replace("index.mdx", "");
    }
  }
});

const nameChangedMap = {
  "/basic-docs/antara/introduction-to-antara.html": "/antara/",
  "/basic-docs/smart-chains/smart-chain-tutorials/subatomic.html":
    "/komodo-defi-framework/",
  "/basic-docs/smart-chains/introduction-to-smart-chain-documentation.html":
    "/smart-chains/",
  "/basic-docs/atomicdex/atomicdex-methods.html": "/komodo-defi-framework/api/",
  "/": "/",
  "/basic-docs/atomicdex/atomicdex-beta/create-a-new-wallet-using-atomicdex-mobile.html":
    "/komodo-defi-framework/mobile/create-new-wallet-on-komodo-mobile-wallet/",
  "/basic-docs/atomicdex/atomicdex-setup/get-started-atomicdex.html":
    "/komodo-defi-framework/setup/",
  "/basic-docs/atomicdex/atomicdex-tutorials/introduction-to-atomicdex.html":
    "/komodo-defi-framework/tutorials/",
  "/basic-docs/atomicdex/introduction-to-atomicdex.html": "/komodo-defi-framework/tutorials/",
  "/mmV2/LP/atomicdex-api-docker-telegram.html":
    "/komodo-defi-framework/tutorials/api-docker-telegram/",
  "/basic-docs/atomicdex/atomicdex-tutorials/add-coin-to-atomicdex-desktop.html":
    "/komodo-defi-framework/tutorials/listing-a-new-coin/",
  "/basic-docs/atomicdex/atomicdex-tutorials/listing-a-coin-on-atomicdex.html":
    "/komodo-defi-framework/tutorials/listing-a-new-coin/",
  "/basic-docs/atomicdex-api-20-dev/account_balance_tasks.html":
    "/komodo-defi-framework/api/v20-dev/task_account_balance/",
  "/basic-docs/atomicdex-api-20-dev/coin_activation_tasks.html":
    "/komodo-defi-framework/api/v20-dev/task_enable_qtum/",
  "/basic-docs/atomicdex-api-20-dev/trezor_initialisation.html":
    "/komodo-defi-framework/api/v20-dev/task_init_trezor/",
  "/basic-docs/atomicdex-api-20-dev/withdraw_tasks.html":
    "/komodo-defi-framework/api/v20-dev/task_withdraw/",
  "/basic-docs/atomicdex-api-20-dev/zhtlc_coins.html":
    "/komodo-defi-framework/api/v20-dev/task_enable_z_coin/",
  "/basic-docs/smart-chains/smart-chain-tutorials/betdapp.html":
    "/smart-chains/setup/dexp2p/",
  "/basic-docs/smart-chains/smart-chain-tutorials/checklist-new-coin.html":
    "/smart-chains/tutorials/smart-chain-api-basics/",
  "/basic-docs/smart-chains/smart-chain-tutorials/introduction-to-smart-chain-tutorials.html":
    "/smart-chains/tutorials/",
  "/basic-docs/start-here/core-technology-discussions/introduction.html":
    "/start-here/core-technology-discussions/",
  "/basic-docs/start-here/learning-launchpad/learning-path-outline.html":
    "/start-here/learning-launchpad/",
  "/basic-docs/start-here/about-komodo-platform/about-komodo-platform.html":
    "/start-here/about-komodo-platform/",
  "/cc-jl/introduction.html": "/historical/cc-jl/",
  "/whitepaper/introduction.html": "/historical/whitepaper/",
  "/komodo/installation.html": "/komodo/",
  "/komodo/access-remote-daemon-ssh.html":
    "/komodo-defi-framework/tutorials/setup-komodefi-api-aws/",
  "/komodo/info.html": "/smart-chains/setup/ecosystem-launch-parameters/",
  "/komodo/multisig-transactions-on-komodo-or-assetchains.html": "/komodo/multisig-transactions-on-komodo-or-smartchains/",
  "/notary/setup-Komodo-Notary-Node.html": "/notary/",
  "/notary/generate-privkeys-third-party-coins-from-passphrase.html":
    "/notary/generate-privkeys-for-third-party-coins-from-passphrase/",
  "/notary/update-Komodo-manually.html": "/notary/update-komodo-manually/",
  "/notary/useful-commands-Komodo-Notary-Node.html":
    "/notary/useful-commands-for-komodo-notary-node/",
  "/komodo/block-1M-changes.html": "/komodo/block-1m-changes/",
  "/komodo/dPoW-conf.html": "/komodo/dpow-conf/",
  "/komodo/setup-electrumX-server.html": "/komodo/setup-electrumx-server/",
  "/komodo/using-Key-Value.html": "/komodo/using-key-value/",
  "/qa/atomicDEX-PRO/build.html": "/qa/komodo-desktop-wallet-build/",
  "/qa/atomicDEX-quickstart.html": "/qa/komodefi-api-quickstart/",
  "/qa/debug-Komodo.html": "/qa/debug-komodo/",
  "/qa/extract-swap-data-atomicDEX-log.html":
    "/qa/extract-swap-data-komodo-wallet-log/",
  "/qa/recover-atomicDEX-mobile-swap-desktop.html":
    "/qa/recover-komodo-mobile-wallet-swap-on-desktop/",
  "/resources/third-party-repos-resources.html": "/resources/third-party/",
  "/resources/list-all-KomodoPlatform-repos-links.html": "/resources/",
  "/basic-docs/antara/activate-antara-smartchain.html":
    "/antara/tutorials/activate-antara-smartchain/",
  "/basic-docs/antara/test-use-write-integrate-antara.html":
    "/antara/tutorials/test-use-write-integrate-antara/",
  "/basic-docs/atomicdex/atomicdex-tutorials/atomicdex-walkthrough.html":
    "/komodo-defi-framework/tutorials/api-walkthrough/",
  "/basic-docs/atomicdex/atomicdex-tutorials/atomicdex-metrics.html": "/komodo-defi-framework/tutorials/api-metrics/",
  "/basic-docs/atomicdex/atomicdex-tutorials/setup-atomicdex-aws.html": "/komodo-defi-framework/tutorials/setup-komodefi-api-aws/",
  "/basic-docs/atomicdex/atomicdex-tutorials/additional-information-about-atomicdex.html": "/komodo-defi-framework/tutorials/additional-information/",
  "/basic-docs/atomicdex/atomicdex-beta/restore-wallet-using-atomicdex-mobile.html": "/komodo-defi-framework/mobile/restore-wallet-on-komodo-mobile-wallet/",
  "/basic-docs/atomicdex/atomicdex-beta/add-and-activate-coins-on-atomicdex-mobile.html": "/komodo-defi-framework/mobile/add-and-activate-coins-on-komodo-mobile-wallet/",
  "/basic-docs/atomicdex/atomicdex-beta/withdraw-or-send-funds-using-atomicdex-mobile.html": "/komodo-defi-framework/mobile/withdraw-or-send-funds-on-komodo-mobile-wallet/",
  "/basic-docs/atomicdex/atomicdex-beta/perform-cross-chain-atomic-swaps-using-atomicdex-mobile.html": "/komodo-defi-framework/mobile/perform-cross-chain-atomic-swaps-on-komodo-mobile-wallet/",
  "/basic-docs/atomicdex/atomicdex-beta/view-ongoing-orders-and-swap-history-on-atomicdex-mobile.html": "/komodo-defi-framework/setup/view-ongoing-orders-and-swap-history-on-komodo-mobile-wallet/",
  "/basic-docs/atomicdex/atomicdex-beta/recover-seed-on-atomicdex-mobile.html": "/komodo-defi-framework/mobile/recover-seed-on-komodo-mobile-wallet/",
  "/basic-docs/atomicdex/atomicdex-beta/delete-seed-from-atomicdex-mobile.html": "/komodo-defi-framework/mobile/delete-seed-on-komodo-mobile-wallet/",
};

for (const path in nameChangedMap) {
  pathObj[path] = nameChangedMap[path];
}

fs.writeFileSync("./utils/Redirect-map.json", JSON.stringify(pathObj, null, 2));

const baseUrl = "https://komodoplatform.com/en/docs";
let arrRedirects = [];
const transformPaths = (obj) => {
  Object.entries(obj).forEach(([key, value]) => {
    const outputString = `${key} ${baseUrl}${value};`;
    arrRedirects.push(outputString);
  });
};

transformPaths(pathObj);
fs.writeFileSync("./utils/Redirect-map.txt", arrRedirects.join("\n"));

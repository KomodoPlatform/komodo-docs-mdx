import fs from "fs";
import { constants } from "./constants.js";

const fileData = JSON.parse(fs.readFileSync("./utils/_fileData.json", 'utf8'));

const Sitemap = (fileData) => {
    let siteMap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1" xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">`;
    for (const path of Object.keys(fileData)) {
        siteMap =
            siteMap +
            `
    <url>
        <loc>${constants.domain +
            constants.basePath +
            (path === "/" ? "/" : path + "/")
            }</loc>
        <lastmod>${fileData[path].dateModified}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>1.0</priority>
    </url>
`;
    }
    siteMap = siteMap + `</urlset>`;
    return siteMap;
};

fs.writeFileSync("./utils/_sitemap.xml", Sitemap(fileData), {
    encoding: "utf8",
    flag: "w",
});
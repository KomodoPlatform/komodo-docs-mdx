const fs = require("fs");

const json1 = require("./_fileData.json");

// Extract the keys from the jsonObject and store them in an array
let array1 = Object.keys(json1);

const json2 = require("./_fileData_old_documentation_mod.json");

let array2 = Object.keys(json2);

// Function to check if a string starts with "mmvl" or "komodo"
function startsWithMMVLorKomodo(str) {
  return (
    str.startsWith("/mmV1") 
  );
}

array2 = array2.filter((item) => !startsWithMMVLorKomodo(item));

const difference1 = array2.filter((item) => !array1.includes(item));

console.log("Elements in old but not in new:", difference1);

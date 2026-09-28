// Shared CSV text guard for every export. Spreadsheet software treats a cell
// that starts with =, +, - or @ (including after spaces or control characters)
// as a formula, so those cells get a leading apostrophe before quoting.
export function guardCsvText(value){
  const text=String(value??'');
  return /^[\s\u0000-\u001f]*[=+\-@]/.test(text)?"'"+text:text;
}

export function csvCell(value){
  return '"'+guardCsvText(value).replaceAll('"','""')+'"';
}

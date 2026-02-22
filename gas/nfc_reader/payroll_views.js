var PAYROLL_VIEW_TIMEZONE = "Asia/Tokyo";
var PAYROLL_VIEW_RAW_SHEET = "payroll_raw";

var PAYROLL_VIEW_SUMMARY_THIS = "Summary_ThisMonth";
var PAYROLL_VIEW_SUMMARY_PREV = "Summary_PrevMonth";
var PAYROLL_VIEW_THIS = "ThisMonth";
var PAYROLL_VIEW_PREV = "PrevMonth";

var PAYROLL_VIEW_EMP_LABELS = {
  "emp01": "Sample_User",
  "emp02": "Sample_User",
  "emp03": "Sample_User"
};

function refreshPayrollViews() {
  if (!SPREADSHEET_ID) throw new Error("SPREADSHEET_ID_EMPTY");
  var ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  var raw = ss.getSheetByName(PAYROLL_VIEW_RAW_SHEET);
  if (!raw) throw new Error("PAYROLL_RAW_NOT_FOUND");

  var rows = pv_readPayrollRaw_(raw);

  var ymThis = pv_monthKey_(new Date());
  var ymPrev = pv_prevMonthKey_(ymThis);

  var emps = pv_unionEmps_(rows, ymThis, ymPrev);
  var nameMap = pv_nameMap_(rows, ymThis, ymPrev);

  var empsDetailSet = {};
  for (var e0 = 0; e0 < emps.length; e0++) empsDetailSet[emps[e0]] = 1;
  if (PAYROLL_VIEW_EMP_LABELS) {
    for (var k in PAYROLL_VIEW_EMP_LABELS) {
      if (Object.prototype.hasOwnProperty.call(PAYROLL_VIEW_EMP_LABELS, k)) empsDetailSet[k] = 1;
    }
  }
  var empsDetail = Object.keys(empsDetailSet);
  empsDetail.sort(pv_empSort_);

  pv_ensureSheetName_(ss, "summary_this", PAYROLL_VIEW_SUMMARY_THIS);
  pv_ensureSheetName_(ss, "summary_prev", PAYROLL_VIEW_SUMMARY_PREV);

  pv_buildSummary_(ss, PAYROLL_VIEW_SUMMARY_THIS, rows, ymThis, emps, nameMap);
  pv_buildSummary_(ss, PAYROLL_VIEW_SUMMARY_PREV, rows, ymPrev, emps, nameMap);

  var used = {};
  used[PAYROLL_VIEW_SUMMARY_THIS] = true;
  used[PAYROLL_VIEW_SUMMARY_PREV] = true;

  var order = [PAYROLL_VIEW_SUMMARY_THIS, PAYROLL_VIEW_SUMMARY_PREV];

  for (var i = 0; i < empsDetail.length; i++) {
    var emp = empsDetail[i];
    var base = pv_empTabBase_(emp, nameMap[emp]);
    var tabThis = pv_pickSheetName_(used, base + "_" + PAYROLL_VIEW_THIS, emp);
    var tabPrev = pv_pickSheetName_(used, base + "_" + PAYROLL_VIEW_PREV, emp);

    pv_ensureSheetName_(ss, emp + "_this", tabThis);
    pv_ensureSheetName_(ss, emp + "_prev", tabPrev);

    pv_buildDetail_(ss, tabThis, rows, ymThis, emp, nameMap);
    pv_buildDetail_(ss, tabPrev, rows, ymPrev, emp, nameMap);

    order.push(tabThis);
    order.push(tabPrev);
  }

  pv_reorderSheets_(ss, order, PAYROLL_VIEW_RAW_SHEET);
}

function pv_monthKey_(d) {
  return Utilities.formatDate(d, PAYROLL_VIEW_TIMEZONE, "yyyy-MM");
}

function pv_prevMonthKey_(ym) {
  var y = parseInt(ym.slice(0, 4), 10);
  var m = parseInt(ym.slice(5, 7), 10);
  m -= 1;
  if (m <= 0) {
    m = 12;
    y -= 1;
  }
  return String(y) + "-" + (m < 10 ? "0" + m : String(m));
}

function pv_unionEmps_(rows, ymA, ymB) {
  var set = {};
  for (var i = 0; i < rows.length; i++) {
    var d = rows[i].date;
    if (!d) continue;
    var ym = d.slice(0, 7);
    if (ym !== ymA && ym !== ymB) continue;
    var emp = rows[i].emp;
    if (!emp) continue;
    set[emp] = 1;
  }
  var out = Object.keys(set);
  out.sort(pv_empSort_);
  return out;
}

function pv_empSort_(a, b) {
  var ra = pv_empRank_(a);
  var rb = pv_empRank_(b);
  if (ra !== rb) return ra - rb;
  return String(a).localeCompare(String(b));
}

function pv_empRank_(emp) {
  var m = String(emp || "").match(/(\d+)/);
  if (!m) return 1000000;
  var n = parseInt(m[1], 10);
  return isNaN(n) ? 1000000 : n;
}

function pv_nameMap_(rows, ymA, ymB) {
  var m = {};
  for (var i = 0; i < rows.length; i++) {
    var d = rows[i].date;
    if (!d) continue;
    var ym = d.slice(0, 7);
    if (ym !== ymA && ym !== ymB) continue;
    var emp = rows[i].emp;
    if (!emp) continue;
    var name = pv_cellStr_(rows[i].name);
    if (name) m[emp] = name;
  }
  return m;
}

function pv_empTabBase_(emp, name) {
  var n = pv_empDisplay_(emp, name);
  if (!n) n = emp;
  return pv_safeSheetName_(n);
}

function pv_buildSummary_(ss, sheetName, rows, ym, emps, nameMap) {
  var agg = {};
  for (var i = 0; i < emps.length; i++) {
    agg[emps[i]] = { min: 0, yen: 0, flags: {} };
  }

  for (var j = 0; j < rows.length; j++) {
    var rec = rows[j];
    if (!rec || !rec.emp) continue;
    if (!rec.date) continue;
    if (rec.date.slice(0, 7) !== ym) continue;

    if (!agg[rec.emp]) agg[rec.emp] = { min: 0, yen: 0, flags: {} };
    agg[rec.emp].min += pv_cellInt_(rec.min);
    agg[rec.emp].yen += pv_cellInt_(rec.yen);

    for (var k = 0; k < rec.flags.length; k++) {
      var f = rec.flags[k];
      agg[rec.emp].flags[f] = 1;
    }

    var nm = pv_cellStr_(rec.name);
    if (nm) nameMap[rec.emp] = nm;
  }

  var values = [["EmpID", "Name", "Month", "Min", "Hour", "Cost", "Check", "Flags"]];
  for (var x = 0; x < emps.length; x++) {
    var emp = emps[x];
    var a = agg[emp] || { min: 0, yen: 0, flags: {} };
    var flagsList = Object.keys(a.flags).sort();
    var needs = flagsList.length > 0 ? 1 : 0;
    var mins = a.min;
    var nm2 = pv_empDisplay_(emp, nameMap[emp]);
    values.push([emp, nm2, ym, mins, mins / 60.0, a.yen, needs, flagsList.join(",")]);
  }

  pv_writeSheet_(ss, sheetName, values, 8);
  pv_applyFormatsSummary_(ss.getSheetByName(sheetName));
}

function pv_empDisplay_(emp, name) {
  var n = pv_cellStr_(name);
  if (n) return n;
  if (PAYROLL_VIEW_EMP_LABELS && PAYROLL_VIEW_EMP_LABELS[emp]) {
    var x = pv_cellStr_(PAYROLL_VIEW_EMP_LABELS[emp]);
    if (x) return x;
  }
  return "";
}

function pv_buildDetail_(ss, sheetName, rows, ym, emp, nameMap) {
  var name = pv_empDisplay_(emp, nameMap[emp]);

  var out = [["Date", "EmpID", "Name", "RawMin", "Min", "Rate", "Cost", "Flags"]];
  for (var i = 0; i < rows.length; i++) {
    var r = rows[i];
    if (!r || r.emp !== emp) continue;
    if (!r.date) continue;
    if (r.date.slice(0, 7) !== ym) continue;

    var nm = pv_cellStr_(r.name);
    if (nm) name = nm;

    out.push([
      r.date,
      r.emp,
      name,
      pv_cellInt_(r.min_raw),
      pv_cellInt_(r.min),
      pv_cellInt_(r.yen_h),
      pv_cellInt_(r.yen),
      r.flags.join(",")
    ]);
  }

  pv_writeSheet_(ss, sheetName, out, 8);
  pv_applyFormatsDetail_(ss.getSheetByName(sheetName));
}

function pv_writeSheet_(ss, name, values, cols) {
  var sh = ss.getSheets().find(function(s) { return s.getName() === name; });
  if (!sh) sh = ss.insertSheet(name);

  sh.clear();
  if (!values || values.length === 0) return;

  sh.getRange(1, 1, values.length, cols).setValues(values);
  sh.setFrozenRows(1);
  sh.getRange(1, 1, 1, cols).setFontWeight("bold");
}

function pv_applyFormatsSummary_(sh) {
  if (!sh) return;
  sh.setColumnWidth(1, 90);
  sh.setColumnWidth(2, 140);
  sh.setColumnWidth(3, 90);
  sh.setColumnWidth(4, 90);
  sh.setColumnWidth(5, 90);
  sh.setColumnWidth(6, 110);
  sh.setColumnWidth(7, 90);
  sh.setColumnWidth(8, 240);

  var last = sh.getLastRow();
  if (last > 1) {
    sh.getRange(2, 4, last - 1, 1).setNumberFormat("0");
    sh.getRange(2, 5, last - 1, 1).setNumberFormat("0.00");
    sh.getRange(2, 6, last - 1, 1).setNumberFormat("0");
    sh.getRange(2, 7, last - 1, 1).setNumberFormat("0");
  }
}

function pv_applyFormatsDetail_(sh) {
  if (!sh) return;
  sh.setColumnWidth(1, 110);
  sh.setColumnWidth(2, 90);
  sh.setColumnWidth(3, 140);
  sh.setColumnWidth(4, 90);
  sh.setColumnWidth(5, 90);
  sh.setColumnWidth(6, 90);
  sh.setColumnWidth(7, 110);
  sh.setColumnWidth(8, 260);

  var last = sh.getLastRow();
  if (last > 1) {
    sh.getRange(2, 4, last - 1, 1).setNumberFormat("0");
    sh.getRange(2, 5, last - 1, 1).setNumberFormat("0");
    sh.getRange(2, 6, last - 1, 1).setNumberFormat("0");
    sh.getRange(2, 7, last - 1, 1).setNumberFormat("0");
  }
}

function pv_readPayrollRaw_(sh) {
  var values = sh.getDataRange().getValues();
  if (!values || values.length < 2) return [];

  var head = values[0];
  var idx = {};
  for (var i = 0; i < head.length; i++) {
    var k = pv_cellStr_(head[i]);
    if (k) idx[k] = i;
  }

  var need = ["id", "date", "emp", "min_raw", "min", "yen_h", "yen", "flags"];
  for (var j = 0; j < need.length; j++) {
    if (idx[need[j]] === undefined) throw new Error("PAYROLL_RAW_MISSING_COL:" + need[j]);
  }

  var hasReceived = idx.received_at !== undefined;

  var out = [];
  for (var r = 1; r < values.length; r++) {
    var row = values[r];
    var id = pv_cellStr_(row[idx.id]);
    if (!id) continue;

    var date = pv_cellStr_(row[idx.date]);
    var receivedAt = hasReceived ? pv_cellStr_(row[idx.received_at]) : "";
    if (!date && receivedAt && receivedAt.length >= 10) {
      var d0 = receivedAt.slice(0, 10);
      if (/^\d{4}-\d{2}-\d{2}$/.test(d0)) date = d0;
    }

    out.push({
      id: id,
      date: date,
      emp: pv_cellStr_(row[idx.emp]),
      min_raw: pv_cellInt_(row[idx.min_raw]),
      min: pv_cellInt_(row[idx.min]),
      yen_h: pv_cellInt_(row[idx.yen_h]),
      yen: pv_cellInt_(row[idx.yen]),
      flags: pv_flagsParse_(row[idx.flags]),
      received_at: receivedAt,
      name: idx.name !== undefined ? pv_cellStr_(row[idx.name]) : ""
    });
  }

  return out;
}

function pv_cellInt_(v) {
  if (v === null || v === undefined || v === "") return 0;
  if (typeof v === "number") return Math.floor(v);
  var s = String(v).trim();
  if (!s) return 0;
  var n = parseInt(s, 10);
  return isNaN(n) ? 0 : n;
}

function pv_cellStr_(v) {
  if (v === null || v === undefined) return "";
  if (Object.prototype.toString.call(v) === "[object Date]") {
    var t = v.getTime();
    if (!isNaN(t)) return Utilities.formatDate(v, PAYROLL_VIEW_TIMEZONE, "yyyy-MM-dd");
  }
  return String(v).trim();
}

function pv_flagsParse_(v) {
  if (v === null || v === undefined) return [];
  if (typeof v === "number" && v === 0) return [];
  if (Array.isArray(v)) return pv_flagsClean_(arr);
  var s = String(v).trim();
  if (!s || s === "0") return [];
  if (s[0] === "[" && s[s.length - 1] === "]") {
    try {
      var a = JSON.parse(s);
      if (Array.isArray(a)) return pv_flagsClean_(a);
    } catch (e) {
    }
  }
  return pv_flagsClean_(s.split(","));
}

function pv_flagsClean_(arr) {
  var out = [];
  for (var i = 0; i < arr.length; i++) {
    var s = String(arr[i]).trim();
    if (s) out.push(s);
  }
  out.sort();
  return out;
}

function pv_safeSheetName_(s) {
  var x = String(s || "").trim();
  if (!x) x = "sheet";
  x = x.replace(/[\[\]\*\/\\\?\:]/g, "_");
  if (x.length > 90) x = x.slice(0, 90);
  return x;
}

function pv_pickSheetName_(used, name, emp) {
  var x = pv_safeSheetName_(name);
  if (!used[x]) { used[x] = true; return x; }
  var y = pv_safeSheetName_(x + "_" + emp);
  if (!used[y]) { used[y] = true; return y; }
  var k = 2;
  while (true) {
    var z = pv_safeSheetName_(x + "_" + k);
    if (!used[z]) { used[z] = true; return z; }
    k++;
  }
}

function pv_ensureSheetName_(ss, oldName, newName) {
  var shNew = ss.getSheetByName(newName);
  if (shNew) return;
  var shOld = ss.getSheetByName(oldName);
  if (shOld) shOld.setName(newName);
}

function pv_reorderSheets_(ss, leading, rawName) {
  var want = {};
  for (var i = 0; i < leading.length; i++) want[leading[i]] = true;
  want[rawName] = true;

  var all = ss.getSheets();
  var rest = [];
  for (var j = 0; j < all.length; j++) {
    var n = all[j].getName();
    if (!want[n]) rest.push(n);
  }

  var order = [];
  for (var a = 0; a < leading.length; a++) order.push(leading[a]);
  for (var b = 0; b < rest.length; b++) order.push(rest[b]);
  if (ss.getSheetByName(rawName)) order.push(rawName);

  for (var p = 0; p < order.length; p++) {
    var sh = ss.getSheetByName(order[p]);
    if (!sh) continue;
    ss.setActiveSheet(sh);
    ss.moveActiveSheet(p + 1);
  }
}

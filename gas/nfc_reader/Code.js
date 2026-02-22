var SPREADSHEET_ID = "YOUR_SPREADSHEET_ID_HERE";

var PAYROLL_RAW_SHEET = "payroll_raw";

var PAYROLL_RAW_HEADERS = ["id","date","emp","min_raw","min","yen_h","yen","flags","received_at","name"];

function doPost(e) {
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(30000);

    var bodyText = (e && e.postData && e.postData.contents) ? e.postData.contents : "";
    var body = bodyText ? JSON.parse(bodyText) : {};

    var op = "";
    if (body && typeof body === "object" && !Array.isArray(body)) {
      op = String(body.op || body.action || "").trim().toLowerCase();
    }

    if (op === "clear") {
      return _handleClearLocked_();
    }

    var sh = _getSheet_();

    var records = [];
    if (Array.isArray(body)) records = body;
    else if (body && Array.isArray(body.records)) records = body.records;

    var inserted = 0;
    var updated = 0;
    var skipped = 0;

    if (records && records.length > 0) {
      var needCols = PAYROLL_RAW_HEADERS.length;
      var lastRow = sh.getLastRow();
      var idToRow = {};

      if (lastRow >= 2) {
        var ids = sh.getRange(2, 1, lastRow - 1, 1).getValues();
        for (var r = 0; r < ids.length; r++) {
          var id0 = String(ids[r][0] || "").trim();
          if (id0) idToRow[id0] = r + 2;
        }
      }

      var nowIso = new Date().toISOString();
      var appendRows = [];

      for (var i = 0; i < records.length; i++) {
        var rec = records[i] || {};
        var id = String(rec.id || "").trim();
        if (!id) {
          skipped++;
          continue;
        }

        var target = idToRow[id] || 0;

        var existingName = "";
        if (target > 0) {
          existingName = _readCell_(sh, target, needCols);
        }

        var row = _recordToRow_(rec, nowIso, existingName);

        if (target > 0) {
          sh.getRange(target, 1, 1, needCols).setValues([row]);
          updated++;
        } else {
          appendRows.push(row);
          inserted++;
        }
      }

      if (appendRows.length > 0) {
        sh.getRange(sh.getLastRow() + 1, 1, appendRows.length, PAYROLL_RAW_HEADERS.length).setValues(appendRows);
      }
    }

    SpreadsheetApp.flush();

    var refreshed = false;
    var refreshError = "";

    try {
      if (typeof refreshPayrollViews === "function") {
        refreshPayrollViews();
        refreshed = true;
      } else {
        refreshed = false;
        refreshError = "REFRESH_FUNC_NOT_FOUND";
      }
    } catch (x) {
      refreshed = false;
      refreshError = String(x);
    }

    if (!refreshed) {
      var outNg = { ok: false, inserted: inserted, updated: updated, skipped: skipped, refreshed: false };
      if (refreshError) outNg.refresh_error = refreshError;
      return _json(outNg);
    }

    return _json({ ok: true, inserted: inserted, updated: updated, skipped: skipped, refreshed: true });
  } catch (err) {
    return _json({ ok: false, error: String(err) });
  } finally {
    try {
      lock.releaseLock();
    } catch (e2) {
    }
  }
}

function _handleClearLocked_() {
  try {
    var sh = _getSheet_();
    var needCols = PAYROLL_RAW_HEADERS.length;
    var last = sh.getLastRow();
    var cleared = 0;

    if (last > 1) {
      sh.getRange(2, 1, last - 1, needCols).clearContent();
      cleared = last - 1;
    }

    SpreadsheetApp.flush();

    var refreshed = false;
    var refreshError = "";

    try {
      if (typeof refreshPayrollViews === "function") {
        refreshPayrollViews();
        refreshed = true;
      } else {
        refreshed = false;
        refreshError = "REFRESH_FUNC_NOT_FOUND";
      }
    } catch (x) {
      refreshed = false;
      refreshError = String(x);
    }

    if (!refreshed) {
      var outNg = { ok: false, op: "clear", cleared_rows: cleared, refreshed: false };
      if (refreshError) outNg.refresh_error = refreshError;
      return _json(outNg);
    }

    return _json({ ok: true, op: "clear", cleared_rows: cleared, refreshed: true });
  } catch (err) {
    return _json({ ok: false, error: String(err) });
  }
}

function doGet() {
  try {
    _getSheet_();
    return _json({ ok: true });
  } catch (err) {
    return _json({ ok: false, error: String(err) });
  }
}

function _getSheet_() {
  if (!SPREADSHEET_ID) throw new Error("SPREADSHEET_ID_EMPTY");
  var ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  var sh = ss.getSheetByName(PAYROLL_RAW_SHEET);
  if (!sh) sh = ss.insertSheet(PAYROLL_RAW_SHEET);

  var needCols = PAYROLL_RAW_HEADERS.length;
  var maxCols = sh.getMaxColumns();
  if (maxCols < needCols) sh.insertColumnsAfter(maxCols, needCols - maxCols);

  sh.getRange(1, 1, 1, needCols).setValues([PAYROLL_RAW_HEADERS]);

  return sh;
}

function _readCell_(sh, row, col) {
  try {
    var v = sh.getRange(row, col, 1, 1).getValues()[0][0];
    return String(v || "");
  } catch (e) {
    return "";
  }
}

function _recordToRow_(rec, nowIso, existingName) {
  var id = String(rec.id || "").trim();
  var date = _toCell_(rec.date);
  var emp = _toCell_(rec.emp);

  var minRaw = _toNumOrBlank_(rec.min_raw);
  var min = _toNumOrBlank_(rec.min);
  var yenH = _toNumOrBlank_(rec.yen_h);
  var yen = _toNumOrBlank_(rec.yen);

  var flags = _flagsToCell_(rec.flags);

  var receivedAt = nowIso;

  var name = "";
  if (rec.name !== null && rec.name !== undefined) name = String(rec.name || "");
  else name = String(existingName || "");

  return [id, date, emp, minRaw, min, yenH, yen, flags, receivedAt, name];
}

function _toNumOrBlank_(v) {
  if (v === null || v === undefined || v === "") return "";
  if (typeof v === "number") return v;
  var s = String(v).trim();
  if (!s) return "";
  var n = Number(s);
  return isNaN(n) ? "" : n;
}

function _toCell_(v) {
  if (v === null || v === undefined) return "";
  if (typeof v === "string") return v;
  if (typeof v === "number") return v;
  if (typeof v === "boolean") return v ? "1" : "0";
  try {
    return JSON.stringify(v);
  } catch (e) {
    return String(v);
  }
}

function _flagsToCell_(flags) {
  if (flags === null || flags === undefined) return "";
  if (typeof flags === "string") return flags;
  try {
    return JSON.stringify(flags);
  } catch (e) {
    return String(flags);
  }
}

function _json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

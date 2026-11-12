const $ = (id) => document.getElementById(id);
function now() { return new Date().toLocaleTimeString(); }
function log(message, kind="INFO") {
  const row = document.createElement("div"); row.className = "log-row";
  const time = document.createElement("span"); time.className = "log-time"; time.textContent = `[${now()}]`;
  const info = document.createElement("span"); info.className = "log-info"; info.textContent = `[${kind}] ${message}`;
  row.append(time, info); $("logs").prepend(row);
}
function clearLogs() { $("logs").innerHTML = ""; log("Local activity log cleared."); }
function openConfirm() { $("confirm-text").value = ""; $("confirm-dialog").showModal(); }
function closeConfirm() { $("confirm-dialog").close(); }
function showResult(text, type) { const el=$("result"); el.textContent=text; el.className=`result ${type}`; }
async function refreshStatus() {
  $("connection").textContent = "Checking AWS…";
  try {
    const r = await fetch("/api/status");
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Could not read AWS status");
    $("connection").textContent = `AWS connected · ${data.region}`;
    $("asg-name").textContent = data.asg_name;
    const healthy = data.instances.filter(i => i.health === "Healthy" && i.lifecycle === "InService").length;
    $("capacity").textContent = `${healthy} / ${data.desired}`;
    $("asg-status").textContent = healthy >= data.desired ? "Healthy" : "Recovering / below desired";
    $("asg-status").className = "pill" + (healthy >= data.desired ? "" : " bad");
    $("instance-count").textContent = data.instances.length;
    $("instance-state").textContent = data.instances.length
      ? data.instances.map(i => `${i.id}: ${i.state} · ${i.lifecycle} · ${i.health}`).join("\n")
      : "No instances currently reported by the ASG.";
    $("instance-state").style.whiteSpace = "pre-line";
    $("alarm-name").textContent = data.alarm?.name || "Alarm not found";
    $("alarm-state").textContent = data.alarm?.state || "Not found";
    $("alarm-state").style.color = data.alarm?.state === "ALARM" ? "#ff6680" : data.alarm?.state === "OK" ? "#21d6a0" : "#e9c46a";
    $("alarm-detail").textContent = data.alarm ? `${data.alarm.metric} · ${data.alarm.reason || "No state reason supplied"}` : "Check alarm name and region.";
    $("instances-table").innerHTML = "";
    for (const i of data.instances) {
      const tr = document.createElement("tr");
      [i.id, i.state, i.lifecycle, i.health, `${i.type} / ${i.az}`].forEach(v => { const td=document.createElement("td"); td.textContent=v; tr.appendChild(td); });
      $("instances-table").appendChild(tr);
    }
    log("AWS status refreshed: ASG " + data.asg_name + ", healthy " + healthy + "/" + data.desired + ", alarm " + (data.alarm?.state || "unknown"));
  } catch (e) {
    $("connection").textContent = "AWS not connected";
    log("Status error: " + e.message, "ERROR");
    showResult("Could not read AWS status.\n" + e.message + "\nCheck AWS CLI credentials, permissions, region, and resource names.", "error");
  }
}
async function triggerKillSwitch() {
  if ($("confirm-text").value !== "TRIGGER KILL SWITCH") {
    showResult("Confirmation phrase does not match. No AWS action was sent.", "error"); return;
  }
  closeConfirm();
  const button = $("trigger-button"); button.disabled = true; button.textContent = "Invoking Lambda…";
  $("switch-knob").parentElement.classList.add("on"); $("switch-label").textContent = "TRIGGERING";
  log("User requested kill-switch invocation. Sending request to backend.", "WARN");
  try {
    const r = await fetch("/api/trigger", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({confirmation:$("confirm-text").value})});
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Lambda invocation failed");
    showResult(JSON.stringify(data, null, 2), "success");
    log("Lambda invocation returned. Refreshing AWS status; verify the instance state and ASG recovery.", "INFO");
    await refreshStatus();
  } catch (e) {
    showResult("Trigger failed:\n" + e.message, "error");
    log("Trigger failed: " + e.message, "ERROR");
  } finally {
    button.disabled = false; button.innerHTML = "ϟ &nbsp; Trigger Kill Switch";
    $("switch-knob").parentElement.classList.remove("on"); $("switch-label").textContent = "STANDBY";
  }
}
refreshStatus();
setInterval(refreshStatus, 30000);
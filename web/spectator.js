const token = new URLSearchParams(location.hash.slice(1)).get('token') || '';
const base = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}`;
const statusElement = document.querySelector('#status');
const promptElement = document.querySelector('#prompt');
const recordingElement = document.querySelector('#recording');
const phaseElement = document.querySelector('#phase');
const taskCountElement = document.querySelector('#task-count');
const totalCountElement = document.querySelector('#total-count');
const frameCountElement = document.querySelector('#frame-count');
const qualityPanelElement = document.querySelector('#quality-panel');
const qualityBadgeElement = document.querySelector('#quality-badge');
const episodeProgressElement = document.querySelector('#episode-progress');
const qualityHzElement = document.querySelector('#quality-hz');
const qualityInputElement = document.querySelector('#quality-input');
const qualityWriterElement = document.querySelector('#quality-writer');
const qualityReasonsElement = document.querySelector('#quality-reasons');
const successTextElement = document.querySelector('#success-text');
const recentListElement = document.querySelector('#recent-list');
const viewportElement = document.querySelector('#viewport');
const fullscreenButtonElement = document.querySelector('#fullscreen-button');
const fullscreenRecordingElement = document.querySelector('#fullscreen-recording');
const fullscreenPhaseElement = document.querySelector('#fullscreen-phase');
const fullscreenTaskCountElement = document.querySelector('#fullscreen-task-count');
const fullscreenTotalCountElement = document.querySelector('#fullscreen-total-count');
const menuElement = document.querySelector('#menu');
const menuTitleElement = document.querySelector('#menu-title');
const menuBodyElement = document.querySelector('#menu-body');
const menuItemsElement = document.querySelector('#menu-items');
const canvas = document.querySelector('#preview');
const context = canvas.getContext('2d');
let socket, reconnectTimer, statusReceivedAt = 0, transferMs = 0, decodeMs = 0;
let frameNumber = 0, drawnFrame = 0, lastMessage = 0;
let pendingFrame = null, decodeRunning = false;
let envEpoch = null;

function syncFullscreenButton() {
  fullscreenButtonElement.textContent=document.fullscreenElement ? '退出全屏' : '⛶ 全屏仿真视角';
}

fullscreenButtonElement.addEventListener('click', async () => {
  if (document.fullscreenElement) await document.exitFullscreen();
  else await viewportElement.requestFullscreen();
});
document.addEventListener('fullscreenchange', syncFullscreenButton);

function renderQuality(msg, input, cycle, writer) {
  const frames=Number(msg.frames || 0);
  const wallHz=Number(msg.wall_hz || 0);
  const previewAge=Number(msg.preview_transport?.age_ms ?? 0);
  const isRecording=msg.phase === 'recording';
  const reasons=[];
  let level='ok';
  const warn=text => { reasons.push(text); if (level === 'ok') level='warning'; };
  const error=text => { reasons.push(text); level='error'; };

  if (writer.writer_error) error('录制写入器异常，请停止并检查本条数据。');
  if (isRecording && (!msg.input_fresh || input.timed_out)) error('控制输入已超时。');
  if (writer.backpressure) warn(`写入队列出现背压 ${writer.queue_depth || 0}/${writer.queue_capacity || 0}。`);
  if (isRecording && (input.seq_gaps || 0) > 0) warn(`本次连接累计发现 ${input.seq_gaps} 个输入序号间隙。`);
  if (isRecording && (!input.left_tracking || !input.right_tracking)) warn('左右手柄未同时保持 tracking。');
  if (isRecording && (msg.ik_failures || 0) > 0) warn(`累计 IK 失败 ${msg.ik_failures} 次。`);
  if (isRecording && previewAge > 1000) warn(`监看画面已滞后 ${Math.round(previewAge)} ms。`);
  if (isRecording && (cycle.p95 || 0) > 200) warn(`控制周期 P95 为 ${cycle.p95} ms。`);

  qualityPanelElement.dataset.level=level;
  qualityBadgeElement.textContent=isRecording ? {ok:'状态良好',warning:'需要关注',error:'异常'}[level] : '待录制';
  episodeProgressElement.textContent=`${frames} 帧 · ${(frames / 25).toFixed(1)} 秒`;
  qualityHzElement.textContent=`${wallHz || 0} Hz`;
  qualityInputElement.textContent=msg.input_fresh ? `新鲜 · ${input.effective_age_ms ?? '-'} ms` : '未就绪';
  qualityWriterElement.textContent=writer.writer_alive ? `正常 · ${writer.queue_depth || 0}/${writer.queue_capacity || 0}` : (isRecording ? '未运行' : '待录制');
  qualityReasonsElement.replaceChildren(...reasons.map(text => {
    const item=document.createElement('li'); item.textContent=text; return item;
  }));
}

function renderRecent(episodes) {
  const recent=(episodes || []).slice(0,5);
  if (!recent.length) {
    const item=document.createElement('li'); item.className='empty'; item.textContent='当前任务暂无已验收记录';
    recentListElement.replaceChildren(item);
    return;
  }
  recentListElement.replaceChildren(...recent.map(episode => {
    const item=document.createElement('li'); item.className='recent-item';
    const title=document.createElement('b'); title.textContent=episode.name.replace('.hdf5','');
    const result=document.createElement('span'); result.className=episode.success ? 'recent-ok' : 'recent-fail';
    result.textContent=`${episode.success ? '成功' : '未成功'} · ${episode.frames} 帧`;
    item.append(title,result); return item;
  }));
}

function renderVrMenu(ui) {
  if (!ui?.open) {
    menuElement.hidden=true;
    menuItemsElement.replaceChildren();
    return;
  }
  menuElement.hidden=false;
  menuTitleElement.textContent=ui.title || 'VR 菜单';
  menuBodyElement.textContent=(ui.body || []).join('\n');
  menuItemsElement.replaceChildren(...(ui.items || []).map((label,index) => {
    const item=document.createElement('li');
    item.textContent=`${index === ui.selected ? '› ' : ''}${label}`;
    item.classList.toggle('selected',index === ui.selected);
    return item;
  }));
  menuItemsElement.querySelector('.selected')?.scrollIntoView({block:'nearest'});
}

function connect() {
  if (!token) { statusElement.textContent='缺少连接凭证。'; return; }
  socket = new WebSocket(`${base}/video?token=${encodeURIComponent(token)}`);
  socket.binaryType='blob';
  socket.onopen=() => {
    lastMessage=performance.now();
    recordingElement.dataset.state='starting';
    recordingElement.textContent='○ 已连接，等待录制状态';
  };
  socket.onmessage=async event => {
    lastMessage=performance.now();
    if (typeof event.data === 'string') {
      const msg=JSON.parse(event.data);
      if (envEpoch !== null && msg.env_epoch !== envEpoch) {
        pendingFrame=null; context.fillStyle='#080e15'; context.fillRect(0,0,1280,720);
      }
      envEpoch=msg.env_epoch;
      statusReceivedAt=performance.now();
      const phase={starting:'启动中',ready:'已就绪',recording:'录制中'}[msg.phase] || msg.phase;
      const input=msg.input || {}, cycle=msg.cycle_ms || {}, writer=msg.recording_writer || {};
      const counts=msg.episode_counts || {};
      const taskCount=Number(counts[msg.task] || 0);
      const totalCount=Object.values(counts).reduce((sum,value) => sum + Number(value || 0),0);
      phaseElement.textContent=phase || '未知';
      taskCountElement.textContent=`${taskCount} 条`;
      totalCountElement.textContent=`${totalCount} 条`;
      frameCountElement.textContent=`${msg.frames || 0} 帧`;
      fullscreenPhaseElement.textContent=`运行状态：${phase || '未知'}`;
      fullscreenTaskCountElement.textContent=`当前任务已验收：${taskCount} 条`;
      fullscreenTotalCountElement.textContent=`全部已验收：${totalCount} 条`;
      renderVrMenu(msg.vr_ui);
      if (writer.writer_error) {
        recordingElement.dataset.state='error';
        recordingElement.textContent='● 录制写入异常';
        fullscreenRecordingElement.dataset.state='error';
        fullscreenRecordingElement.textContent='● 录制写入异常';
      } else if (msg.phase === 'recording') {
        recordingElement.dataset.state='recording';
        recordingElement.textContent=`● 正在录制 · ${msg.frames || 0} 帧`;
        fullscreenRecordingElement.dataset.state='recording';
        fullscreenRecordingElement.textContent=`● 录制中 · ${msg.frames || 0} 帧`;
      } else {
        recordingElement.dataset.state='idle';
        recordingElement.textContent='○ 当前未录制';
        fullscreenRecordingElement.dataset.state='idle';
        fullscreenRecordingElement.textContent='○ 未录制';
      }
      const step=msg.step_profile || {}, obs=msg.observation_profile || {};
      renderQuality(msg,input,cycle,writer);
      successTextElement.textContent=msg.task_info?.success || '等待任务成功标准…';
      renderRecent(msg.episodes);
      statusElement.textContent=`${msg.task || ''} · ${phase} · epoch ${msg.env_epoch ?? '-'} · tick ${msg.sim_tick ?? '-'} · ${msg.wall_hz || 0} Hz\n`+
        `录制 ${msg.phase === 'recording' ? '是' : '否'} · 当前 ${msg.frames || 0} 帧 · 当前任务已验收 ${taskCount} 条 · 全部任务已验收 ${totalCount} 条\n`+
        `输入 ${input.state || '未知'} · 收到/应用 ${input.received_seq ?? '-'}/${input.applied_seq ?? '-'} · 年龄 ${input.effective_age_ms ?? '-'} ms · tracking L/R ${input.left_tracking ? '有' : '无'}/${input.right_tracking ? '有' : '无'}\n`+
        `遥操 ${msg.teleop_allowed ? '允许' : '保持'} · 原因 ${msg.hold_reason || '-'} · IK ${JSON.stringify(msg.ik_status || {})}\n`+
        `周期 ms 当前/p50/p95/p99/max ${cycle.current ?? '-'}/${cycle.p50 ?? '-'}/${cycle.p95 ?? '-'}/${cycle.p99 ?? '-'}/${cycle.max ?? '-'}\n`+
        `IK ${step.solve_ms ?? '-'} · physics ${step.physics_ms ?? '-'} · render ${obs.render_ms ?? '-'} (${obs.render_calls ?? '-'}次) · capture ${obs.capture_ms ?? '-'} · writer ${writer.queue_depth ?? 0}/${writer.queue_capacity ?? 0}${writer.backpressure ? ' 背压' : ''}\n`+
        `预览帧 ${msg.preview_transport?.frame_seq ?? '-'} · 年龄 ${msg.preview_transport?.age_ms ?? '-'} ms · 传输 ${Math.round(transferMs)} ms · 解码 ${Math.round(decodeMs)} ms · 生命周期 ${msg.lifecycle?.phase || msg.operation?.phase || phase}`;
      promptElement.textContent=`任务：${msg.task_info?.prompt_zh || '等待任务 Prompt…'}`;
      return;
    }
    const currentFrame=++frameNumber;
    pendingFrame={blob:event.data,frame:currentFrame,transfer:Math.max(0,performance.now()-statusReceivedAt)};
    if (!decodeRunning) decodeLatest();
  };
  socket.onclose=() => {
    statusElement.textContent='画面连接已断开，正在重连…';
    recordingElement.dataset.state='error';
    recordingElement.textContent='● 监看连接已断开';
    fullscreenRecordingElement.dataset.state='error';
    fullscreenRecordingElement.textContent='● 监看连接已断开';
    fullscreenPhaseElement.textContent='运行状态：连接断开';
    phaseElement.textContent='连接断开';
    renderVrMenu(null);
    if (!reconnectTimer) reconnectTimer=setTimeout(() => { reconnectTimer=null; connect(); },1500);
  };
}
async function decodeLatest() {
  decodeRunning=true;
  while (pendingFrame) {
    const item=pendingFrame; pendingFrame=null;
    const started=performance.now();
    const bitmap=await createImageBitmap(item.blob);
    if (item.frame > drawnFrame) {
      context.drawImage(bitmap,0,0,1280,720);
      context.fillStyle='#fff'; context.font='24px sans-serif';
      context.fillText('左夹爪',20,225); context.fillText('头部',610,105); context.fillText('右夹爪',1175,225);
      drawnFrame=item.frame; transferMs=item.transfer; decodeMs=performance.now()-started;
      canvas.dataset.frame=String(item.frame);
    }
    bitmap.close();
  }
  decodeRunning=false;
}
connect();
setInterval(() => { if (socket?.readyState===WebSocket.OPEN && performance.now()-lastMessage>3000) socket.close(); },500);

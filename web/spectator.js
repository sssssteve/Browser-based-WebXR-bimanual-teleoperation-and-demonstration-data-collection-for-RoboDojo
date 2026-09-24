const token = new URLSearchParams(location.hash.slice(1)).get('token') || '';
const base = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}`;
const statusElement = document.querySelector('#status');
const promptElement = document.querySelector('#prompt');
const recordingElement = document.querySelector('#recording');
const canvas = document.querySelector('#preview');
const context = canvas.getContext('2d');
let socket, reconnectTimer, statusReceivedAt = 0, transferMs = 0, decodeMs = 0;
let frameNumber = 0, drawnFrame = 0, lastMessage = 0;
let pendingFrame = null, decodeRunning = false;
let envEpoch = null;

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
      if (writer.writer_error) {
        recordingElement.dataset.state='error';
        recordingElement.textContent='● 录制写入异常';
      } else if (msg.phase === 'recording') {
        recordingElement.dataset.state='recording';
        recordingElement.textContent=`● 正在录制 · ${msg.frames || 0} 帧`;
      } else {
        recordingElement.dataset.state='idle';
        recordingElement.textContent='○ 当前未录制';
      }
      const step=msg.step_profile || {}, obs=msg.observation_profile || {};
      statusElement.textContent=`${msg.task || ''} · ${phase} · epoch ${msg.env_epoch ?? '-'} · tick ${msg.sim_tick ?? '-'} · ${msg.wall_hz || 0} Hz\n`+
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

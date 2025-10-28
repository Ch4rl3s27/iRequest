// Shared Tailwind-based Signatory Dashboard
// Usage per page before including this file:
//   window.DASHBOARD_TITLE = 'Accounting Dashboard';
//   window.SIGNATORY_OFFICE = 'Accounting'; // for general signatories
//   // or for dean views:
//   // window.DEAN_KEY = 'cs' | 'hm';

(function () {
  const isDeanView = typeof window.DEAN_KEY === 'string' && window.DEAN_KEY.length > 0;
  const office = window.SIGNATORY_OFFICE || '';
  const deanKey = window.DEAN_KEY || '';
  const title = window.DASHBOARD_TITLE || (isDeanView ? 'Dean Dashboard' : `${office || 'Signatory'} Dashboard`);

  // Utilities
  function $(selector, ctx) { return (ctx || document).querySelector(selector); }
  function $all(selector, ctx) { return Array.from((ctx || document).querySelectorAll(selector)); }

  function getBadge(status) {
    const s = String(status || '').toLowerCase();
    if (s === 'pending') return '<span class="px-3 py-1 inline-flex items-center gap-1.5 rounded-full bg-yellow-50 text-yellow-600 text-sm font-medium">Pending</span>';
    if (s === 'processing') return '<span class="px-3 py-1 inline-flex items-center gap-1.5 rounded-full bg-blue-50 text-blue-600 text-sm font-medium">Processing</span>';
    if (s === 'released' || s === 'approved' || s === 'completed') return '<span class="px-3 py-1 inline-flex items-center gap-1.5 rounded-full bg-green-50 text-green-600 text-sm font-medium">Approved</span>';
    if (s === 'rejected') return '<span class="px-3 py-1 inline-flex items-center gap-1.5 rounded-full bg-red-50 text-red-600 text-sm font-medium">Rejected</span>';
    return '<span class="px-3 py-1 inline-flex items-center gap-1.5 rounded-full bg-gray-50 text-gray-600 text-sm font-medium">Unknown</span>';
  }

  function debounce(fn, ms) {
    let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn.apply(null, args), ms); };
  }

  // Layout template (Registrar-like)
  const layoutHTML = `
    <div class="flex h-screen bg-gray-50">
      <nav class="hidden md:flex md:w-64 lg:w-72 flex-col bg-blue-600 p-6 text-white">
        <div class="flex items-center gap-3 mb-8">
          <img src="assets/nclogo.png" alt="NC Logo" class="h-8 w-auto">
          <h4 class="text-lg font-semibold">${title}</h4>
        </div>
        <ul class="space-y-2" id="sidebarMenu">
          <li>
            <a class="flex items-center gap-3 px-4 py-2.5 rounded-lg bg-white/10 font-medium cursor-pointer hover:bg-white/20 transition-colors" data-nav="dashboard">
              <i data-lucide="layout-dashboard" class="w-5 h-5"></i>
              Dashboard
            </a>
          </li>
          <li class="mt-8">
            <div class="relative">
              <button class="flex items-center justify-between w-full px-4 py-2.5 rounded-lg font-medium cursor-pointer hover:bg-white/10 transition-colors" id="settingsToggle">
                <div class="flex items-center gap-3">
                  <i data-lucide="settings" class="w-5 h-5"></i>
                  Settings
                </div>
                <i data-lucide="chevron-down" class="w-4 h-4"></i>
              </button>
              <div class="hidden mt-1 ml-4 space-y-1" id="settingsMenu">
                <a class="flex items-center gap-3 px-4 py-2 rounded-lg font-medium cursor-pointer hover:bg-white/10 transition-colors" data-nav="profile">
                  <i data-lucide="user" class="w-4 h-4"></i>
                  Profile
                </a>
                <a class="flex items-center gap-3 px-4 py-2 rounded-lg font-medium cursor-pointer hover:bg-white/10 transition-colors" data-nav="password">
                  <i data-lucide="key" class="w-4 h-4"></i>
                  Change Password
                </a>
              </div>
            </div>
          </li>
        </ul>
        <button class="mt-auto flex items-center justify-center gap-2 w-full px-4 py-2.5 bg-red-500 text-white rounded-lg font-medium hover:bg-red-600 transition-colors" id="logoutBtn">
          <i data-lucide="log-out" class="w-5 h-5"></i>
          Logout
        </button>
      </nav>

      <main class="flex-1 overflow-y-auto">
        <div class="sticky top-0 z-10 bg-white border-b border-gray-200 px-6 py-4">
          <div class="flex items-center justify-between">
            <h5 class="text-xl font-semibold text-gray-800">${title}</h5>
            <div class="flex items-center gap-3">
              <span class="text-sm text-gray-600" id="staffName">${office || 'Staff'}</span>
              <button class="p-2 rounded-full hover:bg-gray-100 transition-colors">
                <i data-lucide="user" class="w-5 h-5 text-gray-600"></i>
              </button>
            </div>
          </div>
        </div>

        <div id="mainContent"></div>
      </main>
    </div>

    <template id="dashboardTemplate">
      <div class="p-6 space-y-6">
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div class="bg-white rounded-xl shadow-sm border border-yellow-200 p-6 hover:shadow-lg transition-all cursor-pointer transform hover:-translate-y-1" data-type="pending">
            <div class="flex items-start justify-between">
              <div>
                <p class="text-sm font-medium text-gray-600">Pending</p>
                <h3 id="pendingCount" class="text-3xl font-bold mt-2 text-yellow-500">0</h3>
              </div>
              <div class="p-3 bg-yellow-50 rounded-lg"><i data-lucide="file-clock" class="w-6 h-6 text-yellow-500"></i></div>
            </div>
          </div>
          <div class="bg-white rounded-xl shadow-sm border border-blue-200 p-6 hover:shadow-lg transition-all cursor-pointer transform hover:-translate-y-1" data-type="processing">
            <div class="flex items-start justify-between">
              <div>
                <p class="text-sm font-medium text-gray-600">Processing</p>
                <h3 id="processingCount" class="text-3xl font-bold mt-2 text-blue-500">0</h3>
              </div>
              <div class="p-3 bg-blue-50 rounded-lg"><i data-lucide="loader-2" class="w-6 h-6 text-blue-500"></i></div>
            </div>
          </div>
          <div class="bg-white rounded-xl shadow-sm border border-green-200 p-6 hover:shadow-lg transition-all cursor-pointer transform hover:-translate-y-1" data-type="approved">
            <div class="flex items-start justify-between">
              <div>
                <p class="text-sm font-medium text-gray-600">Approved/Released</p>
                <h3 id="approvedCount" class="text-3xl font-bold mt-2 text-green-500">0</h3>
              </div>
              <div class="p-3 bg-green-50 rounded-lg"><i data-lucide="check-circle" class="w-6 h-6 text-green-500"></i></div>
            </div>
          </div>
          <div class="bg-white rounded-xl shadow-sm border border-red-200 p-6 hover:shadow-lg transition-all cursor-pointer transform hover:-translate-y-1" data-type="rejected">
            <div class="flex items-start justify-between">
              <div>
                <p class="text-sm font-medium text-gray-600">Rejected</p>
                <h3 id="rejectedCount" class="text-3xl font-bold mt-2 text-red-500">0</h3>
              </div>
              <div class="p-3 bg-red-50 rounded-lg"><i data-lucide="x-circle" class="w-6 h-6 text-red-500"></i></div>
            </div>
          </div>
        </div>

        <div id="searchContainer" class="hidden">
          <div class="relative">
            <i data-lucide="search" class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400"></i>
            <input id="searchInput" class="w-full pl-10 pr-4 py-2 bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" placeholder="Search student or document...">
          </div>
        </div>

        <div id="tablesContainer" class="bg-white rounded-xl shadow-sm overflow-hidden">
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Student</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Course</th>
                  ${isDeanView ? '<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Year</th>' : ''}
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Updated</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody id="listBody" class="bg-white divide-y divide-gray-200"></tbody>
            </table>
          </div>
        </div>
      </div>
    </template>

    <div id="signatureModal" class="hidden fixed inset-0 z-50 items-center justify-center bg-black/40">
      <div class="bg-white rounded-xl shadow-xl w-[560px] max-w-[95vw] p-4">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-lg font-semibold">Draw E-Signature</h3>
          <button id="sigClose" class="p-2 rounded hover:bg-gray-100"><i data-lucide="x" class="w-5 h-5"></i></button>
        </div>
        <div class="space-y-3">
          <canvas id="signatureCanvas" width="480" height="180" class="border border-gray-200 rounded-lg w-full"></canvas>
          <div class="flex items-center justify-end gap-2">
            <button id="sigClear" class="px-3 py-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700">Clear</button>
            <button id="sigReject" class="px-3 py-1.5 rounded-lg bg-red-500 hover:bg-red-600 text-white">Reject</button>
            <button id="sigSave" class="px-3 py-1.5 rounded-lg bg-green-500 hover:bg-green-600 text-white">Save</button>
          </div>
        </div>
      </div>
    </div>
  `;

  // Mount layout
  document.body.className = 'font-poppins bg-gray-50 min-h-screen';
  document.body.innerHTML = layoutHTML;

  if (window.lucide && window.lucide.createIcons) { window.lucide.createIcons(); }

  // Sidebar interactions
  $('#settingsToggle').addEventListener('click', () => {
    $('#settingsMenu').classList.toggle('hidden');
  });
  $('#sidebarMenu [data-nav="dashboard"]').addEventListener('click', () => loadDashboard());
  $('#sidebarMenu [data-nav="profile"]').addEventListener('click', () => loadProfile());
  $('#sidebarMenu [data-nav="password"]').addEventListener('click', () => loadPassword());
  $('#logoutBtn').addEventListener('click', logout);

  // Signature modal
  let currentSignatoryRow = null;
  const modalEl = $('#signatureModal');
  const canvas = $('#signatureCanvas');
  const ctx = canvas.getContext('2d');
  let drawing = false;
  function openSig(row) { currentSignatoryRow = row; modalEl.classList.remove('hidden'); }
  function closeSig() { currentSignatoryRow = null; modalEl.classList.add('hidden'); ctx.clearRect(0,0,canvas.width,canvas.height); }
  function pointerPos(e){ const rect = canvas.getBoundingClientRect(); const x = (e.touches? e.touches[0].clientX : e.clientX) - rect.left; const y = (e.touches? e.touches[0].clientY : e.clientY) - rect.top; return {x,y}; }
  function startDraw(e){ e.preventDefault(); drawing = true; const p = pointerPos(e); ctx.beginPath(); ctx.moveTo(p.x,p.y); }
  function moveDraw(e){ if(!drawing) return; e.preventDefault(); const p = pointerPos(e); ctx.lineWidth = 2; ctx.lineCap = 'round'; ctx.strokeStyle = 'black'; ctx.lineTo(p.x,p.y); ctx.stroke(); ctx.beginPath(); ctx.moveTo(p.x,p.y); }
  function endDraw(){ drawing = false; ctx.beginPath(); }
  canvas.addEventListener('mousedown', startDraw); canvas.addEventListener('mousemove', moveDraw); canvas.addEventListener('mouseup', endDraw); canvas.addEventListener('mouseleave', endDraw);
  canvas.addEventListener('touchstart', startDraw, {passive:false}); canvas.addEventListener('touchmove', moveDraw, {passive:false}); canvas.addEventListener('touchend', endDraw, {passive:false});
  $('#sigClose').addEventListener('click', closeSig);
  $('#sigClear').addEventListener('click', () => ctx.clearRect(0,0,canvas.width,canvas.height));

  // Data API helpers
  function endpoint(kind) {
    if (isDeanView) {
      if (kind === 'pending') return `/api/clearances/pending?dean=${encodeURIComponent(deanKey)}`;
      if (kind === 'approved') return `/api/clearances/approved?dean=${encodeURIComponent(deanKey)}`;
      if (kind === 'rejected') return `/api/clearances/rejected?dean=${encodeURIComponent(deanKey)}`;
    } else {
      const base = `/api/signatories/${kind}`;
      const qs = office ? `?office=${encodeURIComponent(office)}` : '';
      return base + qs;
    }
    return '';
  }

  async function fetchJSON(url, opts) {
    const res = await fetch(url, opts);
    try { return await res.json(); } catch { return {}; }
  }

  async function loadList(kind) {
    // Show full-screen loading
    if (window.showFullScreenLoading) {
      window.showFullScreenLoading(`Loading ${kind} requests...`);
    }
    
    try {
      const tbody = $('#listBody');
      tbody.innerHTML = `
        <tr><td colspan="6" class="px-6 py-6 text-center text-gray-500">Loading ${kind}...</td></tr>
      `;
      const data = await fetchJSON(endpoint(kind));
      tbody.innerHTML = '';
      const rows = (data && (data.data || data.requests)) || [];
      if (!rows.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="px-6 py-6 text-center text-gray-400">No records</td></tr>';
        updateCounts([], kind);
      return;
    }
    rows.forEach(item => {
      const tr = document.createElement('tr');
      tr.className = 'hover:bg-gray-50 transition-colors';
      const studentName = `${item.first_name || item.student_name || ''} ${item.last_name || ''}`.trim() || (item.student_no || '—');
      const course = item.course_name || item.course_code || item.course || '—';
      const year = item.year_level_name || item.year_level || item.year || '';
      const status = item.status || item.fulfillment_status || kind;
      const updated = item.updated_at || item.request_date || item.created_at || '';
      const requestId = item.request_id || item.id || '';
      const signatoryId = item.signatory_id || '';
      tr.dataset.requestId = requestId;
      tr.dataset.signatoryId = signatoryId;
      tr.innerHTML = `
        <td class="px-6 py-4 text-sm text-gray-800">${studentName}</td>
        <td class="px-6 py-4 text-sm text-gray-600">${course}</td>
        ${isDeanView ? `<td class="px-6 py-4 text-sm text-gray-600">${year || '—'}</td>` : ''}
        <td class="px-6 py-4">${getBadge(status)}</td>
        <td class="px-6 py-4 text-sm text-gray-500">${updated ? new Date(updated).toLocaleString() : '—'}</td>
        <td class="px-6 py-4">
          <div class="flex items-center gap-2">
            <button class="px-3 py-1.5 rounded-lg bg-green-500 hover:bg-green-600 text-white text-sm" data-action="approve">Approve</button>
            <button class="px-3 py-1.5 rounded-lg bg-red-500 hover:bg-red-600 text-white text-sm" data-action="reject">Reject</button>
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    });
    updateCounts(rows, kind);
    } finally {
      // Hide full-screen loading
      if (window.hideFullScreenLoading) {
        window.hideFullScreenLoading();
      }
    }
  }

  function updateCounts(rows, activeKind) {
    const allRows = $all('#listBody tr');
    const counts = { pending: 0, processing: 0, approved: 0, rejected: 0 };
    if (rows && rows.length) {
      rows.forEach(r => {
        const s = String(r.status || r.fulfillment_status || activeKind).toLowerCase();
        if (s.includes('process')) counts.processing++;
        else if (s === 'pending') counts.pending++;
        else if (s === 'rejected') counts.rejected++;
        else counts.approved++;
      });
    } else {
      // fallback from DOM
      allRows.forEach(tr => {
        const badge = tr.children[isDeanView ? 3 : 2]?.textContent?.toLowerCase() || '';
        if (badge.includes('pending')) counts.pending++;
        else if (badge.includes('process')) counts.processing++;
        else if (badge.includes('reject')) counts.rejected++;
        else counts.approved++;
      });
    }
    $('#pendingCount').textContent = String(counts.pending);
    $('#processingCount').textContent = String(counts.processing);
    $('#approvedCount').textContent = String(counts.approved);
    $('#rejectedCount').textContent = String(counts.rejected);
  }

  // Actions
  $('#tablesContainer').addEventListener('click', async (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    const action = btn.dataset.action;
    if (!action) return;
    const tr = btn.closest('tr');
    if (!tr) return;
    const signatoryId = Number(tr.dataset.signatoryId || 0);
    if (!signatoryId) return;

    if (action === 'approve') {
      // open signature modal
      openSig(tr);
    } else if (action === 'reject') {
      const { value: reason } = await Swal.fire({
        title: 'Reject Request', input: 'text', inputLabel: 'Reason', inputPlaceholder: 'Enter reason', showCancelButton: true
      });
      if (!reason) return;
      
      try {
        // Show loading state
        if (window.buttonLoadingManager) {
          window.buttonLoadingManager.showLoading(btn, 'Rejecting...', true);
        }
        
        const response = await fetch('/api/signatories/reject', { 
          method: 'POST', 
          headers: { 'Content-Type': 'application/json' }, 
          body: JSON.stringify({ signatory_id: signatoryId, reason }) 
        });
        
        const result = await response.json();
        
        if (!result.ok) {
          if (window.Swal) {
            await Swal.fire({
              title: 'Error',
              text: result.message || 'Failed to reject clearance',
              icon: 'error',
              confirmButtonText: 'OK'
            });
          } else {
            alert(`Error: ${result.message || 'Failed to reject clearance'}`);
          }
          return;
        }
        
        // Success
        if (window.Swal) {
          await Swal.fire({
            title: 'Success',
            text: 'Clearance rejected successfully!',
            icon: 'success',
            confirmButtonText: 'OK'
          });
        }
        
      } catch (error) {
        console.error('Rejection error:', error);
        if (window.Swal) {
          await Swal.fire({
            title: 'Error',
            text: `Network error: ${error.message}`,
            icon: 'error',
            confirmButtonText: 'OK'
          });
        } else {
          alert(`Network error: ${error.message}`);
        }
      } finally {
        // Hide loading state
        if (window.buttonLoadingManager) {
          window.buttonLoadingManager.hideLoading(btn);
        }
      }
      // refresh current list
      showTable(currentTab);
    }
  });

  $('#sigSave').addEventListener('click', async () => {
    if (!currentSignatoryRow) return;
    const signatoryId = Number(currentSignatoryRow.dataset.signatoryId || 0);
    if (!signatoryId) { closeSig(); return; }
    const signature = canvas.toDataURL('image/png');
    
    const saveButton = $('#sigSave');
    try {
      // Show loading state
      if (window.buttonLoadingManager) {
        window.buttonLoadingManager.showLoading(saveButton, 'Saving...', true);
      }
      
      console.log('🔍 Frontend Debug: Sending approval request:', { signatory_id: signatoryId, signature_present: !!signature });
      
      const response = await fetch('/api/signatories/approve', { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ signatory_id: signatoryId, signature }) 
      });
      
      console.log('🔍 Frontend Debug: Response status:', response.status);
      
      const result = await response.json();
      
      if (!result.ok) {
        // Show specific error message from server
        if (window.Swal) {
          await Swal.fire({
            title: 'Error',
            text: result.message || 'Failed to approve clearance',
            icon: 'error',
            confirmButtonText: 'OK'
          });
        } else {
          alert(`Error: ${result.message || 'Failed to approve clearance'}`);
        }
        return;
      }
      
      // Success - show confirmation
      if (window.Swal) {
        await Swal.fire({
          title: 'Success',
          text: 'Clearance approved successfully!',
          icon: 'success',
          confirmButtonText: 'OK'
        });
      }
      
    } catch (error) {
      console.error('Approval error:', error);
      if (window.Swal) {
        await Swal.fire({
          title: 'Error',
          text: `Network error: ${error.message}`,
          icon: 'error',
          confirmButtonText: 'OK'
        });
      } else {
        alert(`Network error: ${error.message}`);
      }
    } finally {
      // Hide loading state
      if (window.buttonLoadingManager) {
        window.buttonLoadingManager.hideLoading(saveButton);
      }
    }
    closeSig();
    showTable(currentTab);
  });

  $('#sigReject').addEventListener('click', async () => {
    if (!currentSignatoryRow) return;
    const signatoryId = Number(currentSignatoryRow.dataset.signatoryId || 0);
    const reason = 'Rejected via modal';
    
    const rejectButton = $('#sigReject');
    try {
      // Show loading state
      if (window.buttonLoadingManager) {
        window.buttonLoadingManager.showLoading(rejectButton, 'Rejecting...', true);
      }
      
      const response = await fetch('/api/signatories/reject', { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ signatory_id: signatoryId, reason }) 
      });
      
      const result = await response.json();
      
      if (!result.ok) {
        if (window.Swal) {
          await Swal.fire({
            title: 'Error',
            text: result.message || 'Failed to reject clearance',
            icon: 'error',
            confirmButtonText: 'OK'
          });
        } else {
          alert(`Error: ${result.message || 'Failed to reject clearance'}`);
        }
        return;
      }
      
      // Success
      if (window.Swal) {
        await Swal.fire({
          title: 'Success',
          text: 'Clearance rejected successfully!',
          icon: 'success',
          confirmButtonText: 'OK'
        });
      }
      
    } catch (error) {
      console.error('Rejection error:', error);
      if (window.Swal) {
        await Swal.fire({
          title: 'Error',
          text: `Network error: ${error.message}`,
          icon: 'error',
          confirmButtonText: 'OK'
        });
      } else {
        alert(`Network error: ${error.message}`);
      }
    } finally {
      // Hide loading state
      if (window.buttonLoadingManager) {
        window.buttonLoadingManager.hideLoading(rejectButton);
      }
    }
    closeSig();
    showTable(currentTab);
  });

  // Search
  $('#searchInput').addEventListener('input', debounce((e) => {
    const q = e.target.value.toLowerCase();
    $all('#listBody tr').forEach(r => { r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none'; });
  }, 200));

  // Tabs via cards
  let currentTab = 'pending';
  function showTable(kind) {
    currentTab = kind;
    $('#searchContainer').classList.remove('hidden');
    
    // Show full-screen loading for tab changes
    if (window.showFullScreenLoading) {
      window.showFullScreenLoading(`Loading ${kind} requests...`);
    }
    
    loadList(kind);
    $all('[data-type]').forEach(c => c.classList.remove('ring-2','ring-offset-2','ring-blue-500'));
    const active = document.querySelector(`[data-type="${kind}"]`);
    if (active) active.classList.add('ring-2','ring-offset-2','ring-blue-500');
  }

  $all('[data-type]').forEach(card => card.addEventListener('click', () => {
    const kind = card.dataset.type;
    if (window.showFullScreenLoading) {
      window.showFullScreenLoading(`Loading ${kind} requests...`);
    }
    showTable(kind);
  }));

  // Views
  async function loadProfile() {
    const container = $('#mainContent');
    container.innerHTML = `
      <div class="p-6">
        <div class="bg-white rounded-xl shadow-sm p-6">
          <h5 class="text-lg font-semibold mb-4">Profile</h5>
          <div id="profileContent" class="text-sm text-gray-600">Loading...</div>
        </div>
      </div>
    `;
    try {
      const data = await fetchJSON('/api/staff/me');
      if (data && data.ok && data.staff_info) {
        const s = data.staff_info;
        const full = s.full_name || `${s.first_name || ''} ${s.last_name || ''}`.trim();
        $('#profileContent').innerHTML = `
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div><div class="text-gray-500">Full Name</div><div class="font-medium">${full}</div></div>
            <div><div class="text-gray-500">Email</div><div class="font-medium">${s.email || '—'}</div></div>
            <div><div class="text-gray-500">Department/Office</div><div class="font-medium">${s.department || office || '—'}</div></div>
            <div><div class="text-gray-500">Contact</div><div class="font-medium">${s.contact_no || '—'}</div></div>
            <div class="md:col-span-2"><div class="text-gray-500">Address</div><div class="font-medium">${s.address || '—'}</div></div>
          </div>
        `;
        const nameEl = $('#staffName'); if (nameEl) nameEl.textContent = full || (office || 'Staff');
      } else {
        $('#profileContent').textContent = 'Unable to load profile.';
      }
    } catch { $('#profileContent').textContent = 'Unable to load profile.'; }
  }

  function loadPassword() {
    const container = $('#mainContent');
    container.innerHTML = `
      <div class="p-6">
        <div class="bg-white rounded-xl shadow-sm p-6 max-w-lg">
          <h5 class="text-lg font-semibold mb-4">Change Password</h5>
          <form id="passwordForm" class="space-y-4">
            <div>
              <label class="block text-sm text-gray-600 mb-1">Current Password</label>
              <input id="currentPassword" type="password" class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label class="block text-sm text-gray-600 mb-1">New Password</label>
              <input id="newPassword" type="password" class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label class="block text-sm text-gray-600 mb-1">Confirm New Password</label>
              <input id="confirmPassword" type="password" class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <button class="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white" type="submit">Update</button>
          </form>
        </div>
      </div>
    `;
    setTimeout(() => {
      const form = $('#passwordForm');
      if (!form) return;
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const current = $('#currentPassword').value;
        const next = $('#newPassword').value;
        const confirm = $('#confirmPassword').value;
        if (!current || !next || !confirm) { Swal.fire('Error','All fields are required','error'); return; }
        if (next !== confirm) { Swal.fire('Error','New Password and Confirm Password do not match','error'); return; }
        
        const submitButton = form.querySelector('button[type="submit"]');
        try {
          // Show loading state
          if (window.buttonLoadingManager && submitButton) {
            window.buttonLoadingManager.showLoading(submitButton, 'Updating Password...', true);
          }
          
          const res = await fetch('/api/dean/change-password', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ current_password: current, new_password: next, confirm_password: confirm }) });
          const data = await res.json();
          if (data && data.ok) Swal.fire('Success','Password updated','success'); else Swal.fire('Error', data.message || 'Failed to update password','error');
        } catch { Swal.fire('Error','Network error','error'); }
        finally {
          // Hide loading state
          if (window.buttonLoadingManager && submitButton) {
            window.buttonLoadingManager.hideLoading(submitButton);
          }
        }
      });
    }, 50);
  }

  async function logout() {
    const r = await Swal.fire({ title:'Logout', text:'Are you sure you want to logout?', icon:'question', showCancelButton:true, confirmButtonText:'Yes, Logout' });
    if (!r.isConfirmed) return;
    try { await fetch('/api/logout', { method: 'POST' }); } catch {}
    await Swal.fire({ title:'Logged Out', icon:'success' });
    window.location.href = 'login.html';
  }

  function loadDashboard() {
    const container = $('#mainContent');
    const tpl = $('#dashboardTemplate');
    container.innerHTML = '';
    container.appendChild(tpl.content.cloneNode(true));
    if (window.lucide && window.lucide.createIcons) { window.lucide.createIcons(); }
    showTable('pending');


  }

  // Kick off
  loadDashboard();
})();



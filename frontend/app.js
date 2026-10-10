const API = '/api';
const ADMIN_TOKEN_KEY = 'event-portal-admin-token';
const STUDENT_TOKEN_KEY = 'event-portal-student-token';
const STUDENT_PROFILE_KEY = 'event-portal-student-profile';
const $ = (selector, root = document) => root.querySelector(selector);
const escapeHtml = (value = '') => String(value).replace(/[&<>"']/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[char]));
const adminToken = () => localStorage.getItem(ADMIN_TOKEN_KEY);
const studentToken = () => localStorage.getItem(STUDENT_TOKEN_KEY);
const studentProfile = () => {
  try { return JSON.parse(localStorage.getItem(STUDENT_PROFILE_KEY) || 'null'); }
  catch { return null; }
};

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body && !headers['Content-Type']) headers['Content-Type'] = 'application/json';
  if (adminToken()) headers['X-Admin-Token'] = adminToken();
  if (studentToken()) headers['X-Student-Token'] = studentToken();
  const response = await fetch(`${API}${path}`, { ...options, headers });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || payload.detail || 'Request failed');
  return payload;
}

function toast(message, isError = false) {
  const element = $('#toast');
  if (!element) return;
  element.textContent = message;
  element.classList.toggle('error', isError);
  element.classList.add('show');
  clearTimeout(toast.timeout);
  toast.timeout = setTimeout(() => element.classList.remove('show'), 3200);
}

function formatDate(value, options = { dateStyle: 'medium', timeStyle: 'short' }) {
  return new Date(value).toLocaleString(undefined, options);
}

function localDateTime(value) {
  const date = new Date(value);
  const offset = date.getTimezoneOffset();
  return new Date(date.getTime() - offset * 60_000).toISOString().slice(0, 16);
}

function syncStudentNav() {
  const link = $('nav a[href="/student-login"]');
  if (!link) return;
  const profile = studentProfile();
  if (studentToken() && profile) {
    link.textContent = `Hi, ${profile.studentName.split(/\s+/)[0]} · Sign out`;
    link.href = '#student-logout';
    link.onclick = (event) => {
      event.preventDefault();
      localStorage.removeItem(STUDENT_TOKEN_KEY);
      localStorage.removeItem(STUDENT_PROFILE_KEY);
      window.location.reload();
    };
  }
}

function renderEventCards(events) {
  const grid = $('#events-grid');
  if (!grid) return;
  if (!events.length) {
    grid.innerHTML = '<div class="empty-state"><span>○</span><h3>No events found</h3><p>Try changing your search or date filter.</p></div>';
    return;
  }
  const signedIn = Boolean(studentToken());
  grid.innerHTML = events.map((event, index) => {
    const full = event.availableSeats <= 0;
    const past = new Date(event.date) <= new Date();
    const action = past ? '<button class="button disabled" disabled>Registration closed</button>'
      : full ? '<button class="button disabled" disabled>Full</button>'
        : signedIn ? `<button class="button primary register-event" data-event-id="${event._id}">Reserve a seat</button>`
          : '<a class="button primary" href="/student-login">Sign in to register</a>';
    return `<article class="event-card" style="--card-index:${index}">
      <div class="event-card-top"><span class="event-category">CAMPUS EVENT</span><span class="seat-pill ${full ? 'full' : ''}">${full ? 'No seats left' : `${event.availableSeats} seats left`}</span></div>
      <div class="event-date-block"><span>${escapeHtml(new Date(event.date).toLocaleDateString(undefined, { month: 'short' }))}</span><strong>${escapeHtml(new Date(event.date).toLocaleDateString(undefined, { day: '2-digit' }))}</strong></div>
      <h3>${escapeHtml(event.title)}</h3><p class="event-description">${escapeHtml(event.description)}</p>
      <div class="event-meta"><span>◷ ${escapeHtml(formatDate(event.date))}</span><span>⌖ ${escapeHtml(event.venue)}</span></div>
      <div class="event-card-bottom"><span>${event.registrationCount || 0} students registered</span>${action}</div>
    </article>`;
  }).join('');
}

function initEventsPage() {
  let allEvents = [];
  const search = $('#event-search');
  const dateFilter = $('#date-filter');
  const status = $('#event-status');
  const applyFilters = () => {
    const term = search.value.trim().toLowerCase();
    const date = dateFilter.value;
    const filtered = allEvents.filter((event) => {
      const haystack = `${event.title} ${event.description} ${event.venue}`.toLowerCase();
      return (!term || haystack.includes(term)) && (!date || event.date.slice(0, 10) === date);
    });
    renderEventCards(filtered);
    status.textContent = `Showing ${filtered.length} of ${allEvents.length} events`;
  };
  const loadEvents = async () => {
    try { allEvents = await api('/events'); applyFilters(); }
    catch (error) {
      status.innerHTML = `<span class="inline-error">${escapeHtml(error.message)}. Check the API and MongoDB connection.</span>`;
      if (!allEvents.length) $('#events-grid').innerHTML = '<div class="empty-state"><h3>Events are temporarily unavailable</h3><p>Refresh in a moment.</p></div>';
    }
  };
  search.addEventListener('input', applyFilters);
  dateFilter.addEventListener('change', applyFilters);
  $('#clear-filters').addEventListener('click', () => { search.value = ''; dateFilter.value = ''; applyFilters(); });
  $('#events-grid').addEventListener('click', async (event) => {
    const button = event.target.closest('.register-event');
    if (!button) return;
    button.disabled = true; button.textContent = 'Saving seat…';
    try {
      await api(`/events/${button.dataset.eventId}/register`, { method: 'POST' });
      toast('Your seat is reserved. See you there!');
      await loadEvents();
    } catch (error) {
      if (error.message.toLowerCase().includes('student')) {
        localStorage.removeItem(STUDENT_TOKEN_KEY);
        window.location.href = '/student-login';
      } else { toast(error.message, true); button.disabled = false; button.textContent = 'Reserve a seat'; }
    }
  });
  loadEvents();
  setInterval(loadEvents, 5000);
}

function initStudentLoginPage() {
  if (studentToken()) { window.location.replace('/events'); return; }
  const loginForm = $('#student-login-form');
  const signupForm = $('#student-signup-form');
  const tabs = [...document.querySelectorAll('[data-auth-tab]')];
  const chooseTab = (mode) => {
    const login = mode === 'login';
    loginForm.classList.toggle('hidden', !login);
    signupForm.classList.toggle('hidden', login);
    tabs.forEach((tab) => tab.classList.toggle('active', tab.dataset.authTab === mode));
    $('#student-auth-title').textContent = login ? 'Welcome to Jain Events' : 'Create your student account';
    $('#student-auth-copy').textContent = login ? 'Sign in to reserve event seats and manage your plans.' : 'Add your college details once, then register for any event.';
  };
  tabs.forEach((tab) => tab.addEventListener('click', () => chooseTab(tab.dataset.authTab)));
  const completeSignIn = (result) => {
    localStorage.setItem(STUDENT_TOKEN_KEY, result.token);
    localStorage.setItem(STUDENT_PROFILE_KEY, JSON.stringify(result.student));
    window.location.href = '/';
  };
  loginForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    try { completeSignIn(await api('/student/login', { method: 'POST', body: JSON.stringify(Object.fromEntries(new FormData(loginForm))) })); }
    catch (error) { toast(error.message, true); }
  });
  signupForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(signupForm));
    data.year = Number(data.year);
    try { completeSignIn(await api('/student/signup', { method: 'POST', body: JSON.stringify(data) })); }
    catch (error) { toast(error.message, true); }
  });
}

function initMyRegistrationsPage() {
  const loginPanel = $('#my-registrations-login');
  const list = $('#my-registrations-list');
  const status = $('#my-registrations-status');
  if (!studentToken()) { loginPanel.classList.remove('hidden'); return; }
  const load = async () => {
    try {
      const [student, items] = await Promise.all([api('/student/me'), api('/my-registrations')]);
      $('.page-intro > p').textContent = `${student.studentName} · ${student.usn} · ${student.branch}, Year ${student.year}`;
      if (!items.length) {
        list.innerHTML = '<div class="empty-state"><h3>No registrations yet</h3><p>Find an event that interests you and reserve a seat.</p><a class="button primary" href="/">Explore events</a></div>';
        status.textContent = ''; return;
      }
      status.textContent = `${items.length} event${items.length === 1 ? '' : 's'} on your list`;
      list.innerHTML = items.map((item) => `<article class="registration-card"><div><span class="event-category">${escapeHtml(item.event.venue)}</span><h3>${escapeHtml(item.event.title)}</h3><p>${escapeHtml(formatDate(item.event.date))} · ${escapeHtml(item.event.venue)}</p><small>${escapeHtml(item.usn || student.usn)} · ${escapeHtml(item.branch || student.branch)}, Year ${escapeHtml(item.year || student.year)} · Reserved ${escapeHtml(formatDate(item.registeredAt))}</small></div><button class="button danger cancel-registration" data-event-id="${item.eventId}">Cancel seat</button></article>`).join('');
    } catch (error) {
      if (error.message.toLowerCase().includes('student')) { localStorage.removeItem(STUDENT_TOKEN_KEY); loginPanel.classList.remove('hidden'); }
      else status.innerHTML = `<span class="inline-error">${escapeHtml(error.message)}</span>`;
    }
  };
  list.addEventListener('click', async (event) => {
    const button = event.target.closest('.cancel-registration');
    if (!button || !window.confirm('Cancel this event registration? The seat will be released.')) return;
    try { await api(`/events/${button.dataset.eventId}/register`, { method: 'DELETE' }); toast('Your registration was cancelled.'); await load(); }
    catch (error) { toast(error.message, true); }
  });
  load();
}

function initAdminLoginPage() {
  if (adminToken()) { window.location.replace('/admin/dashboard'); return; }
  $('#admin-login-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      const result = await api('/admin/login', { method: 'POST', body: JSON.stringify({ password: new FormData(event.currentTarget).get('password') }) });
      localStorage.setItem(ADMIN_TOKEN_KEY, result.token);
      window.location.href = '/admin/dashboard';
    } catch (error) { toast(error.message, true); }
  });
}

function initAdminPage() {
  if (!adminToken()) { window.location.replace('/admin'); return; }
  const eventForm = $('#event-form');
  let registrationChart = null;
  let branchChart = null;
  const loadAdmin = async () => {
    try {
      const [events, stats] = await Promise.all([api('/events'), api('/stats')]);
      const totalSeats = events.reduce((sum, item) => sum + item.totalSeats, 0);
      const freeSeats = events.reduce((sum, item) => sum + item.availableSeats, 0);
      $('#metric-events').textContent = stats.totalEvents;
      $('#metric-registrations').textContent = stats.totalRegistrations;
      $('#metric-students').textContent = stats.totalStudents;
      $('#metric-seats').textContent = freeSeats;
      $('#admin-events').innerHTML = events.map((item) => {
        const fill = item.totalSeats ? Math.round(((item.totalSeats - item.availableSeats) / item.totalSeats) * 100) : 0;
        return `<tr class="event-row" data-open-event="${item._id}"><td><button class="event-name-button" data-open-event="${item._id}">${escapeHtml(item.title)}</button><small>${escapeHtml(item.venue)}</small></td><td>${escapeHtml(formatDate(item.date))}</td><td><div class="seat-cell"><strong>${item.availableSeats}</strong><span> / ${item.totalSeats}</span></div><div class="seat-meter"><i style="width:${fill}%"></i></div></td><td><span class="table-count">${item.registrationCount || 0}</span></td><td class="table-actions"><button class="button mini secondary edit-event" data-id="${item._id}">Edit</button><button class="button mini danger delete-event" data-id="${item._id}">Delete</button></td></tr>`;
      }).join('') || '<tr><td colspan="5">No events yet. Add one below.</td></tr>';
      drawCharts(stats);
    } catch (error) {
      if (error.message.toLowerCase().includes('admin')) { localStorage.removeItem(ADMIN_TOKEN_KEY); window.location.replace('/admin'); }
      else toast(error.message, true);
    }
  };
  const drawCharts = (stats) => {
    if (!window.Chart) return;
    if (registrationChart) registrationChart.destroy();
    if (branchChart) branchChart.destroy();
    const ctx = $('#registration-chart').getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, 280);
    gradient.addColorStop(0, 'rgba(87, 101, 216, .94)');
    gradient.addColorStop(1, 'rgba(119, 133, 241, .28)');
    registrationChart = new Chart(ctx, {
      type: 'bar',
      data: { labels: stats.events.map((item) => item.title), datasets: [{ label: 'Students', data: stats.events.map((item) => item.registrations), backgroundColor: gradient, borderColor: '#5967db', borderWidth: 1, borderRadius: 9, maxBarThickness: 55 }] },
      options: { responsive: true, maintainAspectRatio: false, animation: { duration: 700 }, plugins: { legend: { display: false }, tooltip: { backgroundColor: '#252a43', padding: 12, displayColors: false, callbacks: { label: (ctx) => `${ctx.parsed.y} student${ctx.parsed.y === 1 ? '' : 's'}` } } }, scales: { y: { beginAtZero: true, suggestedMax: Math.max(3, ...stats.events.map((item) => item.registrations)), ticks: { precision: 0, color: '#81869c' }, grid: { color: 'rgba(120,125,155,.12)', drawBorder: false } }, x: { ticks: { color: '#656b82', maxRotation: 28, minRotation: 0 }, grid: { display: false } } } },
    });
    const palette = ['#5967db', '#34a88a', '#efb34e', '#e57883', '#8d6ad6', '#54a7c5', '#8da75e'];
    branchChart = new Chart($('#branch-chart'), {
      type: 'doughnut',
      data: { labels: stats.branches.map((item) => item.branch), datasets: [{ data: stats.branches.map((item) => item.registrations), backgroundColor: palette, borderColor: '#fff', borderWidth: 4, hoverOffset: 8 }] },
      options: { responsive: true, maintainAspectRatio: false, cutout: '68%', plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, pointStyle: 'circle', boxWidth: 7, padding: 16, color: '#656b82', font: { size: 11 } } }, tooltip: { backgroundColor: '#252a43', padding: 12 } } },
    });
  };
  const openEvent = async (id) => {
    try {
      const data = await api(`/events/${id}/registrations`);
      $('#registrations-title').textContent = data.event.title;
      $('#attendee-summary').textContent = `${data.event.venue} · ${formatDate(data.event.date)}`;
      $('#attendee-count').textContent = data.registrations.length;
      $('#attendee-capacity').textContent = `${data.event.totalSeats} total seats · ${data.event.availableSeats} available`;
      $('#registrations-table').innerHTML = data.registrations.map((person) => `<tr><td><strong>${escapeHtml(person.studentName)}</strong></td><td>${escapeHtml(person.usn || '—')}</td><td>${escapeHtml(person.branch || '—')} · Year ${escapeHtml(person.year || '—')}</td><td>${escapeHtml(person.email)}</td><td>${escapeHtml(formatDate(person.registeredAt))}</td></tr>`).join('') || '<tr><td colspan="5" class="no-attendees">No students registered yet.</td></tr>';
      $('#registrations-panel').classList.remove('hidden');
      $('#registrations-panel').scrollIntoView({ behavior: 'smooth', block: 'center' });
    } catch (error) { toast(error.message, true); }
  };
  $('#admin-logout').addEventListener('click', () => { localStorage.removeItem(ADMIN_TOKEN_KEY); window.location.href = '/admin'; });
  $('#refresh-admin').addEventListener('click', loadAdmin);
  $('#close-registrations').addEventListener('click', () => $('#registrations-panel').classList.add('hidden'));
  $('#cancel-edit').addEventListener('click', resetEventForm);
  eventForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!eventForm.reportValidity()) return;
    const values = Object.fromEntries(new FormData(eventForm));
    const id = values.eventId; delete values.eventId;
    values.date = new Date(values.date).toISOString(); values.totalSeats = Number(values.totalSeats);
    try {
      await api(id ? `/events/${id}` : '/events', { method: id ? 'PUT' : 'POST', body: JSON.stringify(values) });
      toast(id ? 'Event updated and seats recalculated.' : 'Event added to the calendar.');
      resetEventForm(); await loadAdmin();
    } catch (error) { toast(error.message, true); }
  });
  $('#admin-events').addEventListener('click', async (event) => {
    const edit = event.target.closest('.edit-event');
    const remove = event.target.closest('.delete-event');
    const open = event.target.closest('[data-open-event]');
    if (edit) {
      try {
        const records = await api('/events');
        const record = records.find((item) => item._id === edit.dataset.id);
        if (!record) return;
        eventForm.elements.eventId.value = record._id;
        eventForm.elements.title.value = record.title;
        eventForm.elements.description.value = record.description;
        eventForm.elements.date.value = localDateTime(record.date);
        eventForm.elements.venue.value = record.venue;
        eventForm.elements.totalSeats.value = record.totalSeats;
        $('#event-form-title').textContent = 'Edit event'; $('#save-event').textContent = 'Save changes'; $('#cancel-edit').classList.remove('hidden');
        eventForm.scrollIntoView({ behavior: 'smooth', block: 'center' });
      } catch (error) { toast(error.message, true); }
      return;
    }
    if (remove) {
      if (!window.confirm('Delete this event and all its registration records?')) return;
      try { await api(`/events/${remove.dataset.id}`, { method: 'DELETE' }); toast('Event and registrations deleted.'); $('#registrations-panel').classList.add('hidden'); await loadAdmin(); }
      catch (error) { toast(error.message, true); }
      return;
    }
    if (open) openEvent(open.dataset.openEvent);
  });
  function resetEventForm() {
    eventForm.reset(); eventForm.elements.eventId.value = '';
    $('#event-form-title').textContent = 'Create an event'; $('#save-event').textContent = 'Create event'; $('#cancel-edit').classList.add('hidden');
  }
  loadAdmin();
  setInterval(loadAdmin, 10000);
}

function initDbViewPage() {
  const warning = $('#db-view-warning');
  const content = $('#db-view-content');
  const refresh = async () => {
    try {
      const data = await api('/admin/db-view');
      warning.classList.add('hidden'); content.classList.remove('hidden');
      $('#events-count').textContent = data.events.length;
      $('#registrations-count').textContent = data.registrations.length;
      $('#students-count').textContent = data.students.length;
      $('#events-json').textContent = JSON.stringify(data.events, null, 2);
      $('#registrations-json').textContent = JSON.stringify(data.registrations, null, 2);
      $('#students-json').textContent = JSON.stringify(data.students, null, 2);
      $('#db-last-updated').textContent = `Last refreshed ${new Date().toLocaleTimeString()}`;
    } catch (error) {
      if (error.message.toLowerCase().includes('admin')) { content.classList.add('hidden'); warning.classList.remove('hidden'); }
      else $('#db-last-updated').textContent = error.message;
    }
  };
  refresh(); setInterval(refresh, 5000);
}

function init() {
  syncStudentNav();
  const page = document.body.dataset.page;
  if (page === 'events') initEventsPage();
  if (page === 'student-login') initStudentLoginPage();
  if (page === 'admin-login') initAdminLoginPage();
  if (page === 'admin') initAdminPage();
  if (page === 'my-registrations') initMyRegistrationsPage();
  if (page === 'db-view') initDbViewPage();
}

document.addEventListener('DOMContentLoaded', init);

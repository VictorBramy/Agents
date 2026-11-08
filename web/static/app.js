// State management
let currentProfile = null;
let allJobs = [];
let currentFilter = 'all';
let currentLangFilter = 'all';
let currentSourceFilter = 'all';
let currentSearch = '';
let activeModalJobId = null;
let uploadTargetLang = 'auto'; // 'he', 'en', or 'auto'

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  loadProfile();
  loadJobs();
  loadSettings();
  loadMetaAgentStatus();
  loadAutonomousThoughts();
  // Continuously refresh autonomous thoughts stream every 15 seconds
  setInterval(loadAutonomousThoughts, 15000);
  // Initialize Polyeda survey agent status
  loadSurveyStatus();
});

// Profile loaders & handlers
async function loadProfile() {
  try {
    const res = await fetch('/api/profile');
    const data = await res.json();
    if (data && data.full_name) {
      currentProfile = data;
      renderProfile(data);
    }
  } catch (err) {
    console.error('Failed to load profile:', err);
  }
}

function renderProfile(profile) {
  document.getElementById('profileName').textContent = profile.full_name || 'פרופיל מועמד';
  document.getElementById('profileSubtext').textContent = profile.summary || 'קורות חיים נותחו בהצלחה';
  document.getElementById('profileSeniority').textContent = profile.seniority || 'לא צוין';
  document.getElementById('profileExp').textContent = profile.years_of_experience ? `~${Math.round(profile.years_of_experience)} שנים` : '--';
  
  const emailSpan = document.querySelector('#profileEmail span');
  if (emailSpan) emailSpan.textContent = profile.email || 'לא זוהה';
  
  const phoneSpan = document.querySelector('#profilePhone span');
  if (phoneSpan) phoneSpan.textContent = profile.phone || 'לא זוהה';

  // Hebrew CV Badge
  const heBadge = document.getElementById('hebrewCvBadge');
  if (profile.has_hebrew_cv) {
    heBadge.textContent = 'הועלה ✓';
    heBadge.className = 'text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800';
  } else {
    heBadge.textContent = 'לא הועלה';
    heBadge.className = 'text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-200 text-slate-600';
  }

  // English CV Badge
  const enBadge = document.getElementById('englishCvBadge');
  if (profile.has_english_cv) {
    enBadge.textContent = 'Uploaded ✓';
    enBadge.className = 'text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800';
  } else {
    enBadge.textContent = 'Not uploaded';
    enBadge.className = 'text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-200 text-slate-600';
  }

  // Target roles tags
  const rolesContainer = document.getElementById('targetRolesContainer');
  rolesContainer.innerHTML = '';
  if (profile.target_roles && profile.target_roles.length > 0) {
    profile.target_roles.forEach(role => {
      const tag = document.createElement('span');
      tag.className = 'px-2.5 py-1 text-xs font-semibold rounded-lg bg-indigo-50 text-brand-700 border border-indigo-100 flex items-center gap-1';
      tag.innerHTML = `<i data-lucide="target" class="w-3 h-3"></i> ${role}`;
      rolesContainer.appendChild(tag);
    });
  } else {
    rolesContainer.innerHTML = '<span class="text-xs text-slate-400 italic">לא צוינו תפקידי יעד</span>';
  }

  // Skills chips
  const skillsContainer = document.getElementById('skillsContainer');
  skillsContainer.innerHTML = '';
  if (profile.skills && profile.skills.length > 0) {
    profile.skills.forEach(skill => {
      const chip = document.createElement('span');
      chip.className = 'px-2 py-0.5 text-xs font-medium rounded-md bg-slate-100 text-slate-700 border border-slate-200/60';
      chip.textContent = skill;
      skillsContainer.appendChild(chip);
    });
  } else {
    skillsContainer.innerHTML = '<span class="text-xs text-slate-400 italic">לא חולצו כישורים</span>';
  }

  lucide.createIcons();
}

function triggerCvUpload(lang) {
  uploadTargetLang = lang;
  document.getElementById('cvFileInput').click();
}

async function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);
  formData.append('lang', uploadTargetLang);

  const langLabel = uploadTargetLang === 'he' ? 'עברית' : 'אנגלית';
  alert(`מעלה ומנתח קורות חיים ב${langLabel}...`);

  try {
    const res = await fetch('/api/profile/upload-cv', {
      method: 'POST',
      body: formData
    });
    const result = await res.json();
    if (res.ok && result.profile) {
      currentProfile = result.profile;
      renderProfile(result.profile);
      loadJobs(); // refresh match scores
      alert(`קורות החיים (${langLabel}) נותחו ונשמרו בהצלחה! הסוכן מוכן להגיש מועמדויות.`);
    } else {
      alert('שגיאה בניתוח הקובץ: ' + (result.detail || 'נסה שוב'));
    }
  } catch (err) {
    console.error(err);
    alert('אירעה שגיאה בעת העלאת הקובץ.');
  } finally {
    event.target.value = '';
    lucide.createIcons();
  }
}

// Jobs loaders & rendering
async function loadJobs() {
  try {
    const query = new URLSearchParams();
    if (currentFilter !== 'all') query.append('status', currentFilter);
    if (currentLangFilter !== 'all') query.append('lang', currentLangFilter);
    if (currentSourceFilter !== 'all') query.append('source', currentSourceFilter);
    if (currentSearch) query.append('search', currentSearch);

    const res = await fetch(`/api/jobs?${query.toString()}`);
    const jobs = await res.json();
    allJobs = jobs;
    renderJobs(jobs);
    updateFilterCounts();
  } catch (err) {
    console.error('Failed to load jobs:', err);
  }
}

function setSourceFilter(source) {
  currentSourceFilter = source;
  const select = document.getElementById('sourceFilterSelect');
  if (select && select.value !== source) select.value = source;
  loadJobs();
}

function renderJobs(jobs) {
  const container = document.getElementById('jobsList');
  const emptyState = document.getElementById('emptyState');
  container.innerHTML = '';

  if (!jobs || jobs.length === 0) {
    emptyState.classList.remove('hidden');
    container.classList.add('hidden');
    return;
  }

  emptyState.classList.add('hidden');
  container.classList.remove('hidden');

  jobs.forEach(job => {
    const card = document.createElement('div');
    card.className = 'job-card bg-white rounded-2xl border border-slate-200/90 p-5 shadow-sm flex flex-col justify-between hover:border-brand-500/50 transition';

    // Badge color according to score
    let scoreColor = 'bg-amber-100 text-amber-800 border-amber-200';
    if (job.match_score >= 80) {
      scoreColor = 'bg-emerald-100 text-emerald-800 border-emerald-200';
    } else if (job.match_score >= 60) {
      scoreColor = 'bg-indigo-100 text-indigo-800 border-indigo-200';
    }

    // Platform / Source badge styling
    let sourceBadgeClass = 'bg-slate-100 text-slate-700 border-slate-200';
    let sourceLabel = job.source || 'Scraper';
    if (job.source === 'LinkedIn') {
      sourceBadgeClass = 'bg-[#0a66c2]/10 text-[#0a66c2] border-[#0a66c2]/30';
      sourceLabel = 'LinkedIn';
    } else if (job.source === 'Drushim') {
      sourceBadgeClass = 'bg-sky-50 text-sky-700 border-sky-200';
      sourceLabel = 'דרושים 🇮🇱';
    } else if (job.source === 'JobMaster') {
      sourceBadgeClass = 'bg-blue-50 text-blue-700 border-blue-200';
      sourceLabel = 'ג\'ובמאסטר 🇮🇱';
    } else if (job.source === 'AllJobs') {
      sourceBadgeClass = 'bg-amber-50 text-amber-800 border-amber-200';
      sourceLabel = 'AllJobs 🇮🇱';
    } else if (job.source === 'Greenhouse') {
      sourceBadgeClass = 'bg-emerald-50 text-emerald-700 border-emerald-200';
      sourceLabel = 'Greenhouse';
    } else if (job.source === 'Comeet') {
      sourceBadgeClass = 'bg-indigo-50 text-indigo-700 border-indigo-200';
      sourceLabel = 'Comeet';
    }

    // Language badge
    const isHebrew = (job.language === 'he');
    const langBadgeHtml = isHebrew 
      ? `<span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200" title="משרה שפורסמה בעברית - תיק הגשה וקו\"ח בעברית">🇮🇱 עברית</span>`
      : `<span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-200" title="English Job Posting - Submission in English">🇺🇸 English</span>`;

    // Already Applied & Cross-Platform duplicate prevention badge
    const isApplied = (job.status === 'applied');
    let appliedBadgeHtml = '';
    if (isApplied) {
      if (job.already_applied_source && job.already_applied_source !== job.source) {
        appliedBadgeHtml = `<span class="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200 flex items-center gap-1" title="הוגשה מועמדות לחברה זו דרך ${job.already_applied_source}. מניעת כפילות פעילה!"><i data-lucide="check-check" class="w-3 h-3 text-rose-600"></i> כבר הוגש ב-${job.already_applied_source}</span>`;
      } else {
        appliedBadgeHtml = `<span class="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1" title="מועמדות הוגשה בהצלחה"><i data-lucide="check" class="w-3 h-3 text-emerald-600"></i> הוגשה מועמדות ✓</span>`;
      }
    }

    // Matching skills tags
    const matchingSkillsHtml = (job.matching_skills || []).slice(0, 4).map(s => 
      `<span class="px-2 py-0.5 text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-100 rounded-md">${s}</span>`
    ).join('');

    card.innerHTML = `
      <div>
        <div class="flex items-start justify-between gap-2 mb-2">
          <div class="flex items-center flex-wrap gap-1.5">
            <span class="text-[11px] font-bold px-2 py-0.5 rounded-full border ${sourceBadgeClass}">${sourceLabel}</span>
            ${langBadgeHtml}
            ${appliedBadgeHtml}
            ${(!isApplied && job.is_easy_apply) ? '<span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 border border-blue-200 flex items-center gap-0.5"><i data-lucide="zap" class="w-3 h-3 text-blue-600"></i> הגשה מהירה</span>' : ''}
          </div>
          <span class="text-xs font-bold px-2.5 py-0.5 rounded-full border ${scoreColor} shrink-0">
            ${job.match_score}% התאמה
          </span>
        </div>

        <h3 class="font-bold text-slate-900 text-base leading-snug line-clamp-2 hover:text-brand-600 transition cursor-pointer" onclick="openJobModal(${job.id})">
          ${job.title}
        </h3>
        <p class="text-xs font-medium text-slate-500 mt-1 flex items-center gap-1.5">
          <i data-lucide="building-2" class="w-3.5 h-3.5"></i>
          <span>${job.company}</span>
          <span class="text-slate-300">•</span>
          <i data-lucide="map-pin" class="w-3.5 h-3.5"></i>
          <span>${job.location || 'ישראל'}</span>
        </p>

        <div class="flex items-center flex-wrap gap-2 mt-2">
          <span class="feature-pill-salary inline-flex items-center gap-1 text-[11px] px-2.5 py-0.5 rounded-full cursor-default" title="הערכת שכר AI חודשית ברוטו מבוססת שוק הייטק ודרישות">
            <i data-lucide="banknote" class="w-3 h-3 text-emerald-600"></i>
            <span>${job.salary_estimate ? job.salary_estimate.short_display : '14K-18K ₪'}</span>
          </span>
          <button onclick="openInterviewCoachModal(${job.id})" class="feature-btn-interview inline-flex items-center gap-1 text-[11px] px-2.5 py-0.5 rounded-xl transition active:scale-95" title="הכן אותי לראיון למשרה זו עם שאלות ותשובות מודל">
            <i data-lucide="mic" class="w-3 h-3 text-purple-600"></i>
            <span>הכן לראיון 🎙️</span>
          </button>
        </div>

        <p class="text-xs text-slate-600 mt-2.5 line-clamp-2 leading-relaxed bg-slate-50/70 p-2.5 rounded-xl border border-slate-100">
          ${job.match_reason || job.description}
        </p>

        <div class="flex flex-wrap gap-1 mt-3">
          ${matchingSkillsHtml}
        </div>
      </div>

      <div class="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
        <select onchange="updateJobStatus(${job.id}, this.value)" class="text-xs font-medium bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 text-slate-700 focus:outline-none focus:ring-1 focus:ring-brand-500">
          <option value="new" ${job.status === 'new' ? 'selected' : ''}>חדש</option>
          <option value="bookmarked" ${job.status === 'bookmarked' ? 'selected' : ''}>שמור ⭐</option>
          <option value="applied" ${job.status === 'applied' ? 'selected' : ''}>הוגשה מועמדות ✓</option>
          <option value="interviewing" ${job.status === 'interviewing' ? 'selected' : ''}>ראיון 📅</option>
          <option value="rejected" ${job.status === 'rejected' ? 'selected' : ''}>נדחה</option>
        </select>

        <div class="flex items-center gap-1.5">
          ${isApplied ? `
            <button onclick="openApplicationKitModal(${job.id})" class="text-xs font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-300 flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition" title="צפה בפרטי המועמדות שהוגשה ומנע הגשה כפולה">
              <i data-lucide="check-check" class="w-3.5 h-3.5 text-emerald-600"></i>
              <span>הוגש (פרטים)</span>
            </button>
          ` : `
            ${(job.source === 'LinkedIn' && job.is_easy_apply) ? `
              <button onclick="triggerLinkedInAutoEasyApply(${job.id})" class="text-xs font-bold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 flex items-center gap-1 px-2.5 py-1.5 rounded-lg active:scale-95 transition" title="הגשה אוטומטית מלאה ב-LinkedIn">
                <i data-lucide="zap" class="w-3.5 h-3.5 text-blue-600"></i>
                <span>Auto Apply</span>
              </button>
            ` : ''}
            <button onclick="openApplicationKitModal(${job.id})" class="text-xs font-bold text-white bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-700 hover:to-indigo-700 flex items-center gap-1.5 px-3 py-1.5 rounded-lg shadow-sm shadow-brand-500/20 active:scale-95 transition" title="השלמת שדות ב-AI והגשת מועמדות מותאמת">
              <i data-lucide="send" class="w-3.5 h-3.5"></i>
              <span>הגשת AI</span>
            </button>
          `}
          <button onclick="openJobModal(${job.id})" class="text-xs font-semibold text-slate-600 hover:text-slate-800 px-2 py-1.5 rounded-lg hover:bg-slate-100 transition" title="צפה בפרטי המשרה המלאים">
            פרטים
          </button>
        </div>
      </div>
    `;

    container.appendChild(card);
  });

  lucide.createIcons();
}

function updateFilterCounts() {
  document.getElementById('countAll').textContent = allJobs.length;
  document.getElementById('countNew').textContent = allJobs.filter(j => j.status === 'new').length;
  document.getElementById('countBookmarked').textContent = allJobs.filter(j => j.status === 'bookmarked').length;
  document.getElementById('countApplied').textContent = allJobs.filter(j => j.status === 'applied').length;
  document.getElementById('countInterviewing').textContent = allJobs.filter(j => j.status === 'interviewing').length;
}

function setFilter(status) {
  currentFilter = status;
  document.querySelectorAll('.status-tab').forEach(tab => tab.classList.remove('active', 'bg-brand-600', 'text-white'));
  event.target.classList.add('active', 'bg-brand-600', 'text-white');
  loadJobs();
}

function setLangFilter(val) {
  currentLangFilter = val;
  loadJobs();
}

let searchTimeout;
function handleSearch(val) {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    currentSearch = val;
    loadJobs();
  }, 300);
}

// Job Scan Trigger
async function triggerJobScan() {
  const btn = document.getElementById('btnScanJobs');
  const icon = btn.querySelector('.scan-icon');
  const text = document.getElementById('scanBtnText');
  const banner = document.getElementById('scanStatusBanner');

  btn.disabled = true;
  icon.classList.add('scanning');
  text.textContent = 'סורק וממיין לפי שפה...';
  banner.classList.remove('hidden');

  try {
    const res = await fetch('/api/jobs/scan', { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      await loadJobs();
      alert(`הסריקה הושלמה בהצלחה!\nנסרקו ${data.total_scraped} משרות רלוונטיות (עברית ואנגלית) עם התאמת שפה אוטומטית.`);
    } else {
      alert('שגיאה בהפעלת הסורק: ' + (data.detail || 'נסה שוב'));
    }
  } catch (err) {
    console.error(err);
    alert('שגיאת תקשורת עם שרת הסוכן.');
  } finally {
    btn.disabled = false;
    icon.classList.remove('scanning');
    text.textContent = 'סרוק משרות עכשיו';
    banner.classList.add('hidden');
    lucide.createIcons();
  }
}

// Modal handling
function openJobModal(jobId) {
  activeModalJobId = jobId;
  const job = allJobs.find(j => j.id === jobId);
  if (!job) return;

  const isHebrew = (job.language === 'he');

  document.getElementById('modalJobTitle').textContent = job.title;
  document.getElementById('modalCompanyLoc').textContent = `${job.company} • ${job.location || 'Israel'} • פורסם: ${job.posted_date || 'לאחרונה'}`;
  document.getElementById('modalSourceBadge').textContent = job.source || 'Scraper';

  // Language badge in modal
  const langBadge = document.getElementById('modalLangBadge');
  langBadge.textContent = isHebrew ? '🇮🇱 משרה בעברית' : '🇺🇸 English Job';
  langBadge.className = `text-xs font-bold px-2.5 py-0.5 rounded-full ${
    isHebrew ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'
  }`;

  const scoreBadge = document.getElementById('modalMatchScore');
  scoreBadge.textContent = `${job.match_score}% התאמה`;
  scoreBadge.className = `text-xs font-bold px-2.5 py-0.5 rounded-full ${
    job.match_score >= 80 ? 'bg-emerald-100 text-emerald-800' : 'bg-indigo-100 text-indigo-800'
  }`;

  document.getElementById('modalMatchReason').textContent = job.match_reason || 'התאמה טכנולוגית מבוססת ניתוח דרישות התפקיד מול קורות החיים.';
  
  // Notice about automatic language matching
  const notice = document.getElementById('modalLangNotice');
  if (isHebrew) {
    notice.innerHTML = `<i data-lucide="check-circle" class="w-3.5 h-3.5 text-blue-600"></i> המשרה בעברית ➜ הסוכן מתאים את הפנייה ומשתמש בקורות החיים בעברית.`;
  } else {
    notice.innerHTML = `<i data-lucide="check-circle" class="w-3.5 h-3.5 text-purple-600"></i> English Job ➜ The agent drafts in English and applies with your English CV.`;
  }

  // Matching & missing skills tags
  const matchingContainer = document.getElementById('modalMatchingSkills');
  matchingContainer.innerHTML = (job.matching_skills || []).map(s => 
    `<span class="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded font-semibold text-[11px]">✓ ${s}</span>`
  ).join('');

  const missingContainer = document.getElementById('modalMissingSkills');
  missingContainer.innerHTML = (job.missing_skills || []).map(s => 
    `<span class="px-2 py-0.5 bg-slate-100 text-slate-600 rounded text-[11px]">+ ${s}</span>`
  ).join('');

  document.getElementById('modalJobDescription').textContent = job.description || 'אין תיאור זמין.';
  document.getElementById('modalStatusSelect').value = job.status || 'new';

  const applyLink = document.getElementById('modalJobApplyLink');
  if (job.url) {
    applyLink.href = job.url;
    applyLink.classList.remove('hidden');
  } else {
    applyLink.classList.add('hidden');
  }

  // Cover letter text & language picker
  const langSelect = document.getElementById('coverLetterLang');
  langSelect.value = isHebrew ? 'he' : 'en';

  const letterArea = document.getElementById('modalCoverLetterText');
  if (job.cover_letter) {
    letterArea.value = job.cover_letter;
  } else {
    letterArea.value = '';
    // Auto-generate matching the job's language
    generateCoverLetterForModal();
  }

  document.getElementById('jobModal').classList.remove('hidden');
  lucide.createIcons();
}

function closeJobModal() {
  document.getElementById('jobModal').classList.add('hidden');
  activeModalJobId = null;
}

async function updateModalJobStatus(status) {
  if (!activeModalJobId) return;
  await updateJobStatus(activeModalJobId, status);
}

async function updateJobStatus(jobId, status) {
  try {
    await fetch(`/api/jobs/${jobId}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    });
    const job = allJobs.find(j => j.id === jobId);
    if (job) job.status = status;
    updateFilterCounts();
  } catch (err) {
    console.error('Failed to update status:', err);
  }
}

async function generateCoverLetterForModal() {
  if (!activeModalJobId) return;

  const btnText = document.getElementById('genLetterBtnText');
  const lang = document.getElementById('coverLetterLang').value;
  btnText.textContent = 'מנסח מכתב מותאם...';

  try {
    const res = await fetch(`/api/jobs/${activeModalJobId}/cover-letter`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ language: lang })
    });
    const data = await res.json();
    if (res.ok && data.cover_letter) {
      document.getElementById('modalCoverLetterText').value = data.cover_letter;
      const job = allJobs.find(j => j.id === activeModalJobId);
      if (job) job.cover_letter = data.cover_letter;
    }
  } catch (err) {
    console.error('Cover letter failed:', err);
  } finally {
    btnText.textContent = 'חולל מכתב מחדש';
  }
}

function copyCoverLetter() {
  const text = document.getElementById('modalCoverLetterText').value;
  if (!text) return;

  navigator.clipboard.writeText(text).then(() => {
    const btn = document.getElementById('copyLetterBtnText');
    const original = btn.textContent;
    btn.textContent = 'הועתק בהצלחה! ✓';
    setTimeout(() => { btn.textContent = original; }, 2000);
  });
}

// Manual Add Job Modal
function openManualModal() {
  document.getElementById('manualModal').classList.remove('hidden');
}

function closeManualModal() {
  document.getElementById('manualModal').classList.add('hidden');
}

async function submitManualJob() {
  const title = document.getElementById('manualTitle').value.trim();
  const company = document.getElementById('manualCompany').value.trim();
  const url = document.getElementById('manualUrl').value.trim();
  const description = document.getElementById('manualDesc').value.trim();

  if (!title || !company || !description) {
    alert('נא למלא שם משרה, שם חברה ותיאור.');
    return;
  }

  try {
    const res = await fetch('/api/jobs/manual-add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, company, url, description })
    });
    const data = await res.json();
    if (res.ok) {
      closeManualModal();
      document.getElementById('manualTitle').value = '';
      document.getElementById('manualCompany').value = '';
      document.getElementById('manualUrl').value = '';
      document.getElementById('manualDesc').value = '';
      await loadJobs();
      const langStr = data.language === 'he' ? 'עברית 🇮🇱' : 'אנגלית 🇺🇸';
      alert(`המשרה נוספה בהצלחה! זוהתה שפה: ${langStr}, ציון התאמת AI: ${data.match_score}%`);
    }
  } catch (err) {
    console.error(err);
    alert('שגיאה בהוספת משרה ידנית.');
  }
}

// Paste CV Modal
function openPasteCvModal(lang) {
  uploadTargetLang = lang;
  const isHe = (lang === 'he');
  document.getElementById('pasteCvModalTitle').textContent = isHe ? 'הדבקת תוכן קורות חיים בעברית 🇮🇱' : 'Paste English Resume Content 🇺🇸';
  document.getElementById('pasteCvSubtext').textContent = isHe ? 'הדבק כאן את הטקסט של קורות החיים שלך בעברית:' : 'Paste your English CV / Resume text here:';
  document.getElementById('pasteCvText').dir = isHe ? 'rtl' : 'ltr';
  document.getElementById('pasteCvModal').classList.remove('hidden');
}

function closePasteCvModal() {
  document.getElementById('pasteCvModal').classList.add('hidden');
}

async function submitPastedCv() {
  const text = document.getElementById('pasteCvText').value.trim();
  if (!text) {
    alert('אנא הדבק תוכן קורות חיים.');
    return;
  }

  const formData = new FormData();
  formData.append('pasted_text', text);
  formData.append('lang', uploadTargetLang);

  try {
    const res = await fetch('/api/profile/upload-cv', {
      method: 'POST',
      body: formData
    });
    const result = await res.json();
    if (res.ok && result.profile) {
      currentProfile = result.profile;
      renderProfile(result.profile);
      closePasteCvModal();
      document.getElementById('pasteCvText').value = '';
      await loadJobs();
      const l = uploadTargetLang === 'he' ? 'עברית' : 'אנגלית';
      alert(`קורות החיים (${l}) נותחו בהצלחה!`);
    } else {
      alert('שגיאה: ' + (result.detail || 'נסה שוב'));
    }
  } catch (err) {
    console.error(err);
    alert('אירעה שגיאה בעיבוד הטקסט.');
  }
}

// Settings Modal
async function loadSettings() {
  try {
    const res = await fetch('/api/settings');
    const data = await res.json();
    if (data.masked_key) {
      document.getElementById('geminiApiKeyInput').placeholder = data.masked_key;
    }
    if (data.search_location) {
      document.getElementById('searchLocationInput').value = data.search_location;
    }
    if (data.masked_linkedin_cookie) {
      document.getElementById('linkedinCookieInput').placeholder = data.masked_linkedin_cookie;
    }

    // Update LinkedIn connection badge
    const badge = document.getElementById('linkedinConnectionBadge');
    if (badge) {
      if (data.linkedin_connected) {
        badge.textContent = 'מחובר ✓';
        badge.className = 'text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200';
      } else {
        badge.textContent = 'לא מחובר';
        badge.className = 'text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-500';
      }
    }
  } catch (err) {
    console.error(err);
  }
}

function openSettingsModal() {
  document.getElementById('settingsModal').classList.remove('hidden');
  loadSettings();
}

function closeSettingsModal() {
  document.getElementById('settingsModal').classList.add('hidden');
}

async function saveSettings() {
  const geminiKey = document.getElementById('geminiApiKeyInput').value.trim();
  const searchLocation = document.getElementById('searchLocationInput').value.trim();
  const linkedinCookie = document.getElementById('linkedinCookieInput').value.trim();

  try {
    await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        gemini_api_key: geminiKey || undefined,
        search_location: searchLocation || undefined,
        linkedin_li_at: linkedinCookie || undefined
      })
    });
    closeSettingsModal();
    alert('ההגדרות נשמרו בהצלחה!');
  } catch (err) {
    console.error(err);
    alert('שגיאה בשמירת ההגדרות.');
  }
}

async function saveLinkedInCookieDirect() {
  const cookieVal = document.getElementById('linkedinCookieInput').value.trim();
  if (!cookieVal) {
    alert('נא להזין או להדביק את ערך העוגייה (li_at).');
    return;
  }
  try {
    const res = await fetch('/api/linkedin/save-cookie', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ li_at: cookieVal })
    });
    if (!res.ok) throw new Error('שגיאה בשמירת העוגייה');
    
    showToast('חשבון LinkedIn חובר בהצלחה!');
    const badge = document.getElementById('linkedinConnectionBadge');
    if (badge) {
      badge.textContent = 'מחובר ✓';
      badge.className = 'text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200';
    }
    document.getElementById('linkedinCookieInput').value = '';
    await loadSettings();
    await loadJobs();
  } catch (err) {
    alert('שגיאה: ' + err.message);
  }
}

function copyLinkedInConsoleSnippet() {
  const code = `fetch('http://127.0.0.1:8080/api/linkedin/save-cookie', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({li_at:document.cookie.match(/li_at=([^;]+)/)[1]})}).then(()=>alert('LinkedIn מחובר בהצלחה לדשבורד!'));`;
  navigator.clipboard.writeText(code);
  showToast('הפקודה הועתקה! פתח את ה-Console (מקש F12) בלינקדאין, הדבק ולחץ Enter.');
}

// ----------------------------------------------------
// AI Application Kit & Form Answering Assistant
// ----------------------------------------------------
let currentKitData = null;

async function openApplicationKitModal(jobId) {
  activeModalJobId = jobId;
  const modal = document.getElementById('applicationKitModal');
  const container = document.getElementById('appKitFieldsContainer');
  
  // Show modal immediately with loading placeholder
  modal.classList.remove('hidden');
  container.innerHTML = `
    <div class="py-12 flex flex-col items-center justify-center text-slate-400 gap-3">
      <div class="w-8 h-8 border-3 border-brand-500 border-t-transparent rounded-full animate-spin"></div>
      <p class="text-xs font-semibold text-slate-600">Google AI Pro מנתח את טופס המשרה, בוחר את קורות החיים ומנסח תשובות לכל השדות...</p>
    </div>
  `;

  try {
    const res = await fetch(`/api/jobs/${jobId}/application-kit`);
    if (!res.ok) throw new Error('Failed to load application kit');
    const kit = await res.json();
    currentKitData = kit;

    // Header info
    document.getElementById('appKitJobTitle').textContent = kit.job_title;
    document.getElementById('appKitCompanyBadge').textContent = kit.company;

    const isHe = (kit.job_language === 'he');
    const langBadge = document.getElementById('appKitLangBadge');
    langBadge.textContent = isHe ? '🇮🇱 עברית' : '🇺🇸 English';
    langBadge.className = isHe 
      ? 'text-xs font-bold px-2 py-0.5 rounded-md bg-blue-100 text-blue-800 border border-blue-200'
      : 'text-xs font-bold px-2 py-0.5 rounded-md bg-purple-100 text-purple-800 border border-purple-200';

    const jobObj = allJobs.find(j => j.id === jobId) || {};
    const scoreBadge = document.getElementById('appKitScoreBadge');
    scoreBadge.textContent = `${jobObj.match_score || 90}% התאמה`;
    scoreBadge.className = 'text-xs font-extrabold px-2.5 py-0.5 rounded-md bg-emerald-100 text-emerald-800 border border-emerald-200';

    // 1. CV Selection Block
    const cv = kit.selected_cv || {};
    const cvBadge = document.getElementById('appKitCvBadge');
    cvBadge.textContent = cv.language === 'he' ? 'טופס בעברית נבחר ✓' : 'English CV Selected ✓';
    cvBadge.className = cv.language === 'he' 
      ? 'text-xs font-bold px-2.5 py-1 rounded-full bg-blue-100 text-blue-800'
      : 'text-xs font-bold px-2.5 py-1 rounded-full bg-purple-100 text-purple-800';

    document.getElementById('appKitCvFileName').textContent = cv.selected_cv_name || 'CV.pdf';
    document.getElementById('appKitCvFileSize').textContent = `${cv.file_size_kb || 114} KB • מסמך PDF מוכן להגשה`;
    document.getElementById('appKitCvDownloadBtn').href = `/api/cv/download/${encodeURIComponent(cv.selected_cv_name)}`;
    document.getElementById('appKitCvRationale').textContent = cv.rationale || 'השפה הותאמה במדויק לשפת פרסום המשרה והחברה.';

    // 2. Form Fields Rendering
    document.getElementById('appKitFieldsCount').textContent = `(סה"כ ${kit.form_fields.length} שדות שנותחו)`;
    container.innerHTML = '';

    kit.form_fields.forEach((f, idx) => {
      const fieldDiv = document.createElement('div');
      fieldDiv.className = 'p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 hover:border-brand-300 transition-colors space-y-1.5';
      
      const reqStar = f.required ? '<span class="text-rose-500 font-bold">*</span>' : '';
      const inputId = `appKitField_${idx}`;

      let inputHtml = '';
      if (f.type === 'textarea') {
        inputHtml = `<textarea id="${inputId}" data-name="${f.name}" rows="3" class="w-full text-xs p-2.5 bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/20 font-sans leading-relaxed">${f.value || ''}</textarea>`;
      } else if (f.type === 'select' && f.options && f.options.length > 0) {
        const opts = f.options.map(opt => `<option value="${opt}" ${opt === f.value ? 'selected' : ''}>${opt}</option>`).join('');
        inputHtml = `<select id="${inputId}" data-name="${f.name}" class="w-full text-xs p-2.5 bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/20">${opts}</select>`;
      } else {
        inputHtml = `<input type="${f.type || 'text'}" id="${inputId}" data-name="${f.name}" value="${(f.value || '').replace(/"/g, '&quot;')}" class="w-full text-xs p-2.5 bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/20">`;
      }

      fieldDiv.innerHTML = `
        <div class="flex items-center justify-between">
          <label class="text-xs font-bold text-slate-800 flex items-center gap-1" for="${inputId}">
            <span>${f.label}</span>
            ${reqStar}
          </label>
          <button type="button" onclick="copySingleFieldValue('${inputId}')" class="text-[11px] font-semibold text-slate-500 hover:text-brand-600 flex items-center gap-1 bg-white px-2 py-0.5 rounded border border-slate-200 shadow-2xs">
            <i data-lucide="copy" class="w-3 h-3"></i>
            <span>העתק</span>
          </button>
        </div>
        ${inputHtml}
        ${f.reason ? `
          <div class="text-[11px] text-slate-500 flex items-start gap-1.5 pt-0.5">
            <i data-lucide="lightbulb" class="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5"></i>
            <span>${f.reason}</span>
          </div>
        ` : ''}
      `;
      container.appendChild(fieldDiv);
    });

    // 3. Cover Letter
    document.getElementById('appKitCoverLetterText').value = kit.cover_letter || '';
    document.getElementById('appKitExternalLink').href = kit.url || '#';

    // Update submit button state if already applied
    const btnSubmit = document.getElementById('btnExecuteSubmit');
    const btnText = document.getElementById('btnExecuteSubmitText');
    if (jobObj.status === 'applied') {
      btnText.textContent = 'המועמדות כבר הוגשה ✓ (לחץ לעדכון מחדש)';
      btnSubmit.className = 'px-5 py-2 text-xs font-bold text-emerald-800 bg-emerald-100 hover:bg-emerald-200 rounded-xl transition inline-flex items-center gap-2';
    } else {
      btnText.textContent = 'הגש מועמדות וסמן כהוגש ✓';
      btnSubmit.className = 'px-5 py-2 text-xs font-bold text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 rounded-xl shadow-md shadow-emerald-600/20 transition active:scale-95 inline-flex items-center gap-2';
    }

    lucide.createIcons();
  } catch (err) {
    console.error(err);
    container.innerHTML = `
      <div class="p-6 text-center text-rose-600 text-xs">
        <p class="font-bold">שגיאה בטעינת תיק ההגשה</p>
        <p class="mt-1 text-slate-500">${err.message}</p>
      </div>
    `;
  }
}

function closeApplicationKitModal() {
  document.getElementById('applicationKitModal').classList.add('hidden');
}

function copySingleFieldValue(inputId) {
  const el = document.getElementById(inputId);
  if (el) {
    navigator.clipboard.writeText(el.value);
    showToast('הועתק ללוח!');
  }
}

function copyAppKitCoverLetter() {
  const txt = document.getElementById('appKitCoverLetterText').value;
  navigator.clipboard.writeText(txt);
  showToast('מכתב הפנייה הועתק ללוח!');
}

function copyAllAppKitAnswers() {
  if (!currentKitData) return;
  const container = document.getElementById('appKitFieldsContainer');
  const inputs = container.querySelectorAll('input, select, textarea');
  
  let formatted = `=== תיק הגשה: ${currentKitData.job_title} @ ${currentKitData.company} ===\n`;
  formatted += `קובץ קורות חיים: ${currentKitData.selected_cv?.selected_cv_name || ''}\n`;
  formatted += `קישור למשרה: ${currentKitData.url || ''}\n\n`;
  formatted += `--- שדות הטופס ותשובות AI ---\n`;

  inputs.forEach(inp => {
    const name = inp.getAttribute('data-name');
    const label = inp.closest('div').querySelector('label span')?.textContent || name;
    formatted += `• ${label}: ${inp.value}\n`;
  });

  formatted += `\n--- מכתב פנייה ---\n`;
  formatted += document.getElementById('appKitCoverLetterText').value;

  navigator.clipboard.writeText(formatted);
  showToast('כל תשובות הטופס ומכתב הפנייה הועתקו ללוח בהצלחה!');
}

async function executeJobApplication() {
  if (!activeModalJobId) return;
  const btn = document.getElementById('btnExecuteSubmit');
  const btnText = document.getElementById('btnExecuteSubmitText');
  
  btn.disabled = true;
  btnText.textContent = 'מגיש מועמדות ושומר נתונים...';

  // Gather field values
  const container = document.getElementById('appKitFieldsContainer');
  const inputs = container.querySelectorAll('input, select, textarea');
  const answers = {};
  inputs.forEach(inp => {
    const name = inp.getAttribute('data-name');
    if (name) answers[name] = inp.value;
  });
  answers['cover_letter'] = document.getElementById('appKitCoverLetterText').value;

  try {
    const res = await fetch(`/api/jobs/${activeModalJobId}/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answers })
    });
    const data = await res.json();
    
    // Update local job state
    const job = allJobs.find(j => j.id === activeModalJobId);
    if (job) job.status = 'applied';
    updateFilterCounts();
    renderJobs(allJobs);

    btnText.textContent = 'הוגש בהצלחה ✓';
    btn.className = 'px-5 py-2 text-xs font-bold text-white bg-emerald-600 rounded-xl transition inline-flex items-center gap-2';

    showToast(data.result?.message || 'המועמדות הוגשה בהצלחה והסטטוס עודכן ל-Applied!');
  } catch (err) {
    console.error(err);
    alert('שגיאה בהגשת המועמדות: ' + err.message);
    btn.disabled = false;
    btnText.textContent = 'הגש מועמדות וסמן כהוגש ✓';
  }
}

// ----------------------------------------------------
// Inspect Custom Job URL Modal
// ----------------------------------------------------
function openInspectUrlModal() {
  document.getElementById('inspectUrlModal').classList.remove('hidden');
  document.getElementById('inspectUrlInput').value = '';
}

function closeInspectUrlModal() {
  document.getElementById('inspectUrlModal').classList.add('hidden');
}

async function submitInspectUrl() {
  const url = document.getElementById('inspectUrlInput').value.trim();
  if (!url) {
    alert('נא להזין קישור למשרה או לטופס.');
    return;
  }

  const btn = document.getElementById('btnRunInspectUrl');
  const btnText = document.getElementById('inspectUrlBtnText');
  btn.disabled = true;
  btnText.textContent = 'מנתח טופס עם Google AI Pro...';

  try {
    const res = await fetch('/api/applications/inspect-url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
    if (!res.ok) throw new Error('שגיאה בניתוח הקישור');
    const kit = await res.json();
    
    closeInspectUrlModal();
    // Reload jobs list so the new job appears
    await loadJobs();
    // Directly open the application kit modal for the analyzed job!
    openApplicationKitModal(kit.job_id);
  } catch (err) {
    console.error(err);
    alert('שגיאה בעיבוד הקישור: ' + err.message);
  } finally {
    btn.disabled = false;
    btnText.textContent = 'נתח טופס והכן הגשה';
  }
}

// Simple Toast Helper
function showToast(msg) {
  let toast = document.getElementById('globalToast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'globalToast';
    toast.className = 'fixed bottom-6 right-6 z-50 bg-slate-900 text-white text-xs font-bold px-4 py-3 rounded-xl shadow-xl flex items-center gap-2 transition-all transform translate-y-4 opacity-0 pointer-events-none';
    document.body.appendChild(toast);
  }
  toast.innerHTML = `<i data-lucide="check-circle" class="w-4 h-4 text-emerald-400"></i> <span>${msg}</span>`;
  lucide.createIcons();
  
  toast.classList.remove('translate-y-4', 'opacity-0', 'pointer-events-none');
  setTimeout(() => {
    toast.classList.add('translate-y-4', 'opacity-0', 'pointer-events-none');
  }, 3500);
}

// ----------------------------------------------------
// LinkedIn Automation Functions
// ----------------------------------------------------
async function openLinkedInLoginWindow() {
  const btn = document.getElementById('btnLinkedInLogin');
  const originalText = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i><span>חלון התחברות נפתח... אנא התחבר בלינקדאין</span>`;
    lucide.createIcons();
  }

  try {
    const res = await fetch('/api/linkedin/login-window', { method: 'POST' });
    const data = await res.json();
    showToast(data.message || 'חלון Chrome נפתח. התחבר לחשבונך.');

    // Poll every 2.5 seconds to detect login completion
    let pollInterval = setInterval(async () => {
      try {
        const sRes = await fetch('/api/settings');
        const sData = await sRes.json();
        if (sData.linkedin_connected) {
          clearInterval(pollInterval);
          if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalText;
            lucide.createIcons();
          }
          const badge = document.getElementById('linkedinConnectionBadge');
          if (badge) {
            badge.textContent = 'מחובר ✓';
            badge.className = 'text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200';
          }
          showToast('התחברת ל-LinkedIn בהצלחה!');
          await loadJobs();
        }
      } catch (e) {
        clearInterval(pollInterval);
      }
    }, 2500);

    setTimeout(() => {
      clearInterval(pollInterval);
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = originalText;
        lucide.createIcons();
      }
    }, 240000);

  } catch (err) {
    console.error(err);
    alert('שגיאה בפתיחת חלון ההתחברות: ' + err.message);
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalText;
      lucide.createIcons();
    }
  }
}

async function triggerLinkedInAutoEasyApply(jobId) {
  const job = allJobs.find(j => j.id === jobId);
  if (!job) return;

  // Verify LinkedIn session is connected
  try {
    const sRes = await fetch('/api/settings');
    const sData = await sRes.json();
    if (!sData.linkedin_connected) {
      alert('חשבון LinkedIn אינו מחובר עדיין. פתח את "הגדרות" והתחבר לחשבונך כדי להפעיל Auto Apply, או לחץ על "הגשת AI" לקבלת תיק הגשה מוכן.');
      openSettingsModal();
      return;
    }
  } catch (err) {
    console.warn(err);
  }

  const modal = document.getElementById('easyApplyModal');
  const title = document.getElementById('easyApplyJobTitle');
  const comp = document.getElementById('easyApplyJobCompany');
  const logsContainer = document.getElementById('easyApplyLogsContainer');
  const banner = document.getElementById('easyApplyStatusBanner');

  title.textContent = job.title;
  comp.textContent = `${job.company} • ${job.location || 'ישראל'}`;
  banner.className = 'p-3 rounded-xl text-xs font-bold hidden';
  logsContainer.innerHTML = `
    <div class="text-blue-400 animate-pulse">⚡ מפעיל אוטומציית Playwright ומנוע Google AI Pro...</div>
  `;

  modal.classList.remove('hidden');

  try {
    const res = await fetch(`/api/jobs/${jobId}/easy-apply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ auto_submit: true, headless: false })
    });
    const result = await res.json();

    logsContainer.innerHTML = '';
    (result.logs || []).forEach(log => {
      const line = document.createElement('div');
      line.className = 'border-b border-slate-800/60 pb-1 text-[11px]';
      if (log.includes('CV')) line.className += ' text-emerald-400 font-bold';
      else if (log.includes('Filled') || log.includes('Checked') || log.includes('Selected')) line.className += ' text-indigo-300';
      else if (log.includes('Error')) line.className += ' text-rose-400 font-bold';
      else line.className += ' text-slate-300';
      line.textContent = log;
      logsContainer.appendChild(line);
    });

    banner.classList.remove('hidden');
    if (result.success && result.submitted) {
      banner.className = 'p-3 rounded-xl text-xs font-bold bg-emerald-50 text-emerald-800 border border-emerald-200 block';
      banner.textContent = `✓ ${result.message}`;
      job.status = 'applied';
      updateFilterCounts();
      renderJobs(allJobs);
    } else if (result.success && !result.submitted) {
      banner.className = 'p-3 rounded-xl text-xs font-bold bg-amber-50 text-amber-800 border border-amber-200 block';
      banner.textContent = `ℹ️ ${result.message}`;
    } else {
      banner.className = 'p-3 rounded-xl text-xs font-bold bg-rose-50 text-rose-800 border border-rose-200 block';
      banner.textContent = `⚠️ ${result.message}`;
    }
  } catch (err) {
    console.error(err);
    logsContainer.innerHTML += `<div class="text-rose-400">שגיאה: ${err.message}</div>`;
  }
}

function closeEasyApplyModal() {
  document.getElementById('easyApplyModal').classList.add('hidden');
}

// ==========================================
// Meta-Agent / Agent Optimizer Client Logic
// ==========================================

let latestAuditData = null;

async function loadMetaAgentStatus() {
  try {
    const res = await fetch('/api/meta-agent/status');
    if (!res.ok) return;
    const data = await res.json();
    latestAuditData = data;
    renderMetaAgentUI(data);
  } catch (err) {
    console.error('[MetaAgent Error]:', err);
  }
}

function renderMetaAgentUI(data) {
  if (!data) return;

  const score = data.health_score || 0;
  
  // 1. Header & Banner Badges
  const navBadge = document.getElementById('navHealthBadge');
  if (navBadge) {
    navBadge.textContent = `${score}`;
    navBadge.className = `text-xs px-2 py-0.5 rounded-full text-white font-bold ${
      score >= 80 ? 'bg-emerald-600' : score >= 60 ? 'bg-amber-600' : 'bg-rose-600'
    }`;
  }

  const barScorePill = document.getElementById('metaHealthScorePill');
  if (barScorePill) {
    barScorePill.textContent = `${score}/100`;
    barScorePill.className = `absolute -bottom-1 -right-1 px-2 py-0.5 text-xs font-bold rounded-full shadow-md ${
      score >= 80 ? 'bg-emerald-400 text-slate-950' : score >= 60 ? 'bg-amber-400 text-slate-950' : 'bg-rose-400 text-white'
    }`;
  }

  const barStatusText = document.getElementById('metaHealthStatusText');
  if (barStatusText) {
    if (score >= 85) {
      barStatusText.textContent = 'מערכת מכוילת ומותאמת 🚀';
      barStatusText.className = 'text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
    } else if (score >= 65) {
      barStatusText.textContent = 'ביצועים טובים - זוהו המלצות לשיפור';
      barStatusText.className = 'text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30';
    } else {
      barStatusText.textContent = 'נדרש כיול וריפוי רכיבים ⚠️';
      barStatusText.className = 'text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30';
    }
  }

  // 2. Modal Top Banner
  const modalVal = document.getElementById('modalHealthScoreValue');
  if (modalVal) {
    modalVal.textContent = `${score}`;
    modalVal.className = `text-2xl font-black ${
      score >= 80 ? 'text-emerald-400' : score >= 60 ? 'text-amber-400' : 'text-rose-400'
    }`;
  }

  const modalSummary = document.getElementById('modalHealthSummaryText');
  if (modalSummary) {
    modalSummary.textContent = data.summary || `ציון בריאות מערכת: ${score}/100`;
  }

  const modalTime = document.getElementById('modalAuditTimestamp');
  if (modalTime && data.run_at) {
    modalTime.textContent = `בדיקה אחרונה: ${data.run_at}`;
  }

  // 3. Subsystem Badges & Details
  const sc = data.scrapers_health || {};
  const mq = data.match_quality || {};
  const bc = data.bilingual_coverage || {};
  const hy = data.db_hygiene || {};

  // Scrapers
  const scBadge = document.getElementById('diagScraperBadge');
  const scDetails = document.getElementById('diagScraperDetails');
  if (scBadge && scDetails) {
    const ghActive = sc.greenhouse ? sc.greenhouse.active_count : 0;
    const ghDead = sc.greenhouse ? sc.greenhouse.dead_count : 0;
    scBadge.textContent = `${sc.score || 0}%`;
    scBadge.className = `text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
      sc.score >= 80 ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
    }`;
    scDetails.textContent = `Greenhouse: ${ghActive} פעילים (${ghDead} מושבתים) • LinkedIn: ${sc.linkedin?.is_connected ? 'מחובר' : 'אורח'}`;
  }

  // Match Engine
  const mqBadge = document.getElementById('diagMatchBadge');
  const mqDetails = document.getElementById('diagMatchDetails');
  if (mqBadge && mqDetails) {
    const fpCount = mq.false_positive_count || 0;
    mqBadge.textContent = `${mq.score || 0}%`;
    mqBadge.className = `text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
      mq.score >= 80 ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
    }`;
    mqDetails.textContent = mq.has_word_boundary_bug 
      ? `אותרו שגיאות מחרוזת (${fpCount} חיובי כוזב)` 
      : `מנוע מכויל (${fpCount} התאמות כוזבות)`;
  }

  // Bilingual Coverage
  const bcBadge = document.getElementById('diagBilingualBadge');
  const bcDetails = document.getElementById('diagBilingualDetails');
  if (bcBadge && bcDetails) {
    bcBadge.textContent = `${bc.score || 0}%`;
    bcBadge.className = `text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
      bc.score >= 80 ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
    }`;
    bcDetails.textContent = `עברית: ${bc.hebrew_roles_count || 0} • אנגלית: ${bc.english_roles_count || 0} ${bc.has_bilingual_cv ? '• קו"ח דו-לשוניים' : ''}`;
  }

  // Hygiene
  const hyBadge = document.getElementById('diagHygieneBadge');
  const hyDetails = document.getElementById('diagHygieneDetails');
  if (hyBadge && hyDetails) {
    hyBadge.textContent = `${hy.score || 0}%`;
    hyBadge.className = 'text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800';
    hyDetails.textContent = `${hy.total_jobs || 0} משרות מאונדקסות • ${hy.unscored_jobs || 0} לא מדורגות`;
  }

  // 4. Render Recommendations
  const recsContainer = document.getElementById('metaRecommendationsContainer');
  const recsCountPill = document.getElementById('recsCountPill');
  const recs = data.recommendations || [];

  if (recsCountPill) {
    recsCountPill.textContent = `${recs.length} המלצות`;
  }

  if (recsContainer) {
    if (recs.length === 0) {
      recsContainer.innerHTML = `
        <div class="p-6 text-center text-xs text-emerald-800 bg-emerald-50 rounded-xl border border-emerald-200">
          ✓ כל המערכות פועלות בצורה אופטימלית! לא נמצאו תקלות או המלצות דחופות.
        </div>
      `;
    } else {
      recsContainer.innerHTML = recs.map(r => {
        let priorityClass = 'bg-slate-100 text-slate-800';
        let priorityLabel = 'מידע';
        if (r.priority === 'CRITICAL') {
          priorityClass = 'bg-rose-100 text-rose-800 border border-rose-200';
          priorityLabel = 'קריטי 🔴';
        } else if (r.priority === 'HIGH') {
          priorityClass = 'bg-amber-100 text-amber-800 border border-amber-200';
          priorityLabel = 'גבוה 🟠';
        } else if (r.priority === 'MEDIUM') {
          priorityClass = 'bg-blue-100 text-blue-800 border border-blue-200';
          priorityLabel = 'בינוני 🟡';
        }

        return `
          <div class="p-4 rounded-xl border border-slate-200 bg-white hover:border-slate-300 transition flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-2xs">
            <div class="space-y-1">
              <div class="flex items-center gap-2">
                <span class="text-[10px] font-bold px-2 py-0.5 rounded-full ${priorityClass}">${priorityLabel}</span>
                <span class="text-[10px] font-semibold text-slate-400">${r.category || ''}</span>
              </div>
              <h5 class="text-xs font-bold text-slate-900">${r.title}</h5>
              <p class="text-[11px] text-slate-600 leading-relaxed max-w-xl">${r.description}</p>
            </div>
            <button onclick="runAutoOptimization('${r.id}')" class="shrink-0 px-3 py-1.5 text-xs font-semibold text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-lg transition flex items-center gap-1 active:scale-95">
              <i data-lucide="wrench" class="w-3.5 h-3.5 text-emerald-600"></i>
              <span>בצע שיפור זה</span>
            </button>
          </div>
        `;
      }).join('');
    }
  }

  // 5. Render Fixes Applied Log (if any)
  const fixes = data.fixes_applied || [];
  const fixesSec = document.getElementById('appliedFixesSection');
  const fixesContainer = document.getElementById('appliedFixesContainer');
  if (fixesSec && fixesContainer) {
    if (fixes.length > 0) {
      fixesSec.classList.remove('hidden');
      fixesContainer.innerHTML = fixes.map(f => `
        <div class="flex items-center gap-2 text-emerald-900 font-medium">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
          <span class="font-bold">${f.title}:</span>
          <span class="text-slate-600">${f.result}</span>
        </div>
      `).join('');
    }
  }

  // 6. Render Features Conceived & Built by Meta-Agent (Feature Lab)
  const featsContainer = document.getElementById('metaConceivedFeaturesContainer');
  const features = data.conceived_features || [
    {
      id: "ai_salary_benchmark",
      name: "מחשבון שכר AI ושווי שוק",
      icon: "banknote",
      status: "deployed",
      version: "1.0",
      description: "הערכת טווחי שכר חודשיים ברוטו לכל משרה בהתבסס על סקרי שכר הייטק ופיננסים ישראליים ודרישות התפקיד.",
      impact: "מוצג ישירות על כל כרטיסיית משרה עם אינדיקטור שכר מהיר."
    },
    {
      id: "interview_prep_coach",
      name: "מאמן ראיונות AI אישי (STAR Method)",
      icon: "mic",
      status: "deployed",
      version: "1.0",
      description: "חיזוי 5 שאלות ראיון מקצועיות ספציפיות לכל משרה, הפקת תשובות מודל מותאמות אישית לקו\"ח, ושאלות לשאול מראיין.",
      impact: "זמין בלחיצה אחת מכרטיסיית המשרה: 'הכן לראיון 🎙️'."
    },
    {
      id: "whatsapp_daily_digest",
      name: "סיכום משרות יומי לוואטסאפ (1-Click Share)",
      icon: "message-circle",
      status: "deployed",
      version: "1.0",
      description: "הודעת סיכום מעוצבת ומוכנה לשליחה מהירה בוואטסאפ עם קישורים ישירים וציוני התאמה.",
      impact: "זמין מכפתור 'סיכום לוואטסאפ' בראש הדשבורד."
    },
    {
      id: "skill_gap_roadmap",
      name: "מפת פערי כישורים ושדרוג קו\"ח",
      icon: "trending-up",
      status: "deployed",
      version: "1.0",
      description: "ניתוח מטא-דאטה של דרישות מעסיקים, זיהוי 3 הכישורים המובילים שחסרים בקו\"ח והמלצות על קורסים פתוחים.",
      impact: "זמין מכפתור 'מפת כישורים' בראש הדשבורד."
    }
  ];

  if (featsContainer) {
    featsContainer.innerHTML = features.map(f => `
      <div class="p-3.5 bg-slate-50 border border-slate-200/90 rounded-xl space-y-2 hover:border-indigo-300 transition shadow-2xs">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div class="w-7 h-7 rounded-lg bg-indigo-50 text-brand-600 flex items-center justify-center border border-indigo-100">
              <i data-lucide="${f.icon || 'sparkles'}" class="w-3.5 h-3.5"></i>
            </div>
            <h5 class="text-xs font-bold text-slate-900">${f.name}</h5>
          </div>
          <span class="text-[9px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">פעיל ומיושם ✓</span>
        </div>
        <p class="text-[11px] text-slate-600 leading-relaxed">${f.description}</p>
        <div class="text-[10px] text-indigo-700 bg-indigo-50/70 p-1.5 rounded-lg border border-indigo-100 flex items-center gap-1">
          <i data-lucide="check" class="w-3 h-3 text-indigo-600 shrink-0"></i>
          <span>${f.impact}</span>
        </div>
      </div>
    `).join('');
  }

  if (window.lucide) {
    lucide.createIcons();
  }
}

function openMetaAgentModal() {
  const modal = document.getElementById('metaAgentModal');
  if (modal) {
    modal.classList.remove('hidden');
    loadMetaAgentStatus();
    loadAutonomousThoughts();
  }
}

function closeMetaAgentModal() {
  const modal = document.getElementById('metaAgentModal');
  if (modal) {
    modal.classList.add('hidden');
  }
}

async function triggerMetaAudit() {
  const icon = document.getElementById('auditSpinIcon');
  if (icon) icon.classList.add('animate-spin');

  try {
    const res = await fetch('/api/meta-agent/audit', { method: 'POST' });
    const data = await res.json();
    latestAuditData = data;
    renderMetaAgentUI(data);
  } catch (err) {
    console.error('Audit failed:', err);
    alert('שגיאה בהפעלת דיאגנוסטיקה.');
  } finally {
    if (icon) icon.classList.remove('animate-spin');
  }
}

async function runAutoOptimization(fixId = null) {
  const btn = document.getElementById('btnQuickOptimizeText');
  const origText = btn ? btn.textContent : '';
  if (btn) btn.textContent = 'מבצע שיפורים ושדרוג אוטונומי... ⚙️';

  try {
    const res = await fetch('/api/meta-agent/optimize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fix_ids: fixId ? [fixId] : null })
    });
    const result = await res.json();
    if (res.ok) {
      await loadMetaAgentStatus();
      await loadJobs(); // refresh rescored jobs immediately in dashboard!
      alert(`השיפורים הוחלו בהצלחה! 🚀\n${result.message}`);
    } else {
      alert(`שגיאה בביצוע אופטימיזציה: ${result.detail || 'נסה שוב'}`);
    }
  } catch (err) {
    console.error('Optimization error:', err);
    alert('שגיאה בהפעלת אופטימיזציה.');
  } finally {
    if (btn) btn.textContent = origText;
  }
}

// ==========================================
// Autonomous Thinking & Actions Stream Logic
// ==========================================

let isAutonomousEnabled = true;

async function loadAutonomousThoughts() {
  try {
    const res = await fetch('/api/meta-agent/thoughts');
    if (!res.ok) return;
    const status = await res.json();
    renderAutonomousThoughtsUI(status);
  } catch (err) {
    console.error('Error fetching autonomous thoughts:', err);
  }
}

function renderAutonomousThoughtsUI(status) {
  if (!status) return;

  isAutonomousEnabled = status.enabled;

  // 1. Live Thought Banner (Above Profile)
  const banner = document.getElementById('metaLiveThoughtBanner');
  if (banner && status.current_thought) {
    banner.textContent = `מחשבה נוכחית: ${status.current_thought}`;
  }

  // 2. Modal Current Thought
  const modalCurThought = document.getElementById('currentThoughtText');
  if (modalCurThought && status.current_thought) {
    modalCurThought.textContent = status.current_thought;
  }

  // 3. Modal Status Badges & Countdown
  const autoBadge = document.getElementById('autoLoopBadge');
  const nextCycle = document.getElementById('autoLoopNextCycle');
  const toggleBtnText = document.getElementById('toggleLoopText');
  const toggleBtnIcon = document.getElementById('toggleLoopIcon');

  if (autoBadge) {
    if (status.is_running && status.enabled) {
      autoBadge.textContent = 'פעיל ברקע 🟢';
      autoBadge.className = 'text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
      if (toggleBtnText) toggleBtnText.textContent = 'השהה מצב רציף';
    } else {
      autoBadge.textContent = 'מושהה ⏸️';
      autoBadge.className = 'text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30';
      if (toggleBtnText) toggleBtnText.textContent = 'הפעל מצב רציף';
    }
  }

  if (nextCycle) {
    nextCycle.textContent = `סבבים שבוצעו: ${status.cycle_count || 0} • בדיקה אחרונה: ${status.last_run || 'זה עתה'} • תדירות: כל ${status.interval_minutes || 10} דקות`;
  }

  const intervalSelect = document.getElementById('autoLoopIntervalSelect');
  if (intervalSelect && status.interval_seconds) {
    intervalSelect.value = String(status.interval_seconds);
  }

  // 4. Render Thoughts Stream
  const container = document.getElementById('autonomousThoughtsContainer');
  const thoughts = status.recent_thoughts || [];

  if (container) {
    if (thoughts.length === 0) {
      container.innerHTML = `
        <div class="text-xs text-slate-400 italic p-3 text-center bg-slate-950/60 rounded-xl border border-slate-800">
          סבב החשיבה הראשון מתבצע ברקע כעת...
        </div>
      `;
    } else {
      container.innerHTML = thoughts.map(t => {
        let typeIcon = 'brain';
        let typeColor = 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20';
        let typeLabel = 'ניתוח';

        if (t.thought_type === 'discovery') {
          typeIcon = 'search';
          typeColor = 'text-blue-400 bg-blue-500/10 border-blue-500/20';
          typeLabel = 'גילוי לוחות';
        } else if (t.thought_type === 'optimization') {
          typeIcon = 'zap';
          typeColor = 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
          typeLabel = 'שיפור אוטונומי';
        } else if (t.thought_type === 'verification') {
          typeIcon = 'check-check';
          typeColor = 'text-teal-400 bg-teal-500/10 border-teal-500/20';
          typeLabel = 'אימות';
        }

        const actionHtml = t.action_taken ? `
          <div class="mt-1.5 p-2 rounded-lg bg-emerald-950/60 border border-emerald-500/30 text-emerald-300 text-[11px] font-medium flex items-center gap-1.5">
            <span class="font-bold">⚡ פעולה שבוצעה:</span>
            <span>${t.action_taken}</span>
          </div>
        ` : '';

        return `
          <div class="p-3 bg-slate-950/80 rounded-xl border border-slate-800 hover:border-slate-700 transition space-y-1">
            <div class="flex items-center justify-between text-[10px]">
              <div class="flex items-center gap-1.5">
                <span class="px-2 py-0.5 rounded-full border font-bold ${typeColor}">${typeLabel}</span>
                <span class="text-slate-400 font-bold">${t.title}</span>
              </div>
              <span class="text-slate-500 font-mono">${t.created_at ? t.created_at.split(' ')[1] : ''}</span>
            </div>
            <p class="text-xs text-slate-300 leading-relaxed font-sans">${t.thought_content}</p>
            ${actionHtml}
          </div>
        `;
      }).join('');
    }
  }

  if (window.lucide) {
    lucide.createIcons();
  }
}

async function triggerImmediateAutonomousCycle() {
  const btn = document.getElementById('btnTriggerCycleModal');
  if (btn) btn.disabled = true;

  try {
    const res = await fetch('/api/meta-agent/trigger-cycle', { method: 'POST' });
    const data = await res.json();
    alert(data.message || 'סבב חשיבה הופעל בהצלחה ברקע!');
    // Poll quickly over 10 seconds to catch progress
    let checks = 0;
    const interval = setInterval(async () => {
      checks++;
      await loadAutonomousThoughts();
      await loadMetaAgentStatus();
      if (checks >= 4) {
        clearInterval(interval);
        if (btn) btn.disabled = false;
      }
    }, 2500);
  } catch (err) {
    console.error('Trigger cycle error:', err);
    alert('שגיאה בהפעלת סבב חשיבה.');
    if (btn) btn.disabled = false;
  }
}

async function changeAutonomousInterval(seconds) {
  try {
    const res = await fetch('/api/meta-agent/toggle-autonomous', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ interval_seconds: parseInt(seconds) })
    });
    const status = await res.json();
    renderAutonomousThoughtsUI(status);
  } catch (err) {
    console.error('Change interval error:', err);
  }
}

async function toggleAutonomousLoop() {
  try {
    const newStatus = !isAutonomousEnabled;
    const res = await fetch('/api/meta-agent/toggle-autonomous', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: newStatus })
    });
    const status = await res.json();
    renderAutonomousThoughtsUI(status);
  } catch (err) {
    console.error('Toggle error:', err);
    alert('שגיאה בשינוי מצב אוטונומי.');
  }
}

// ==========================================
// Handlers for Conceived & Built AI Features
// ==========================================

// 1. AI Interview Prep Coach
async function openInterviewCoachModal(jobId) {
  const modal = document.getElementById('interviewCoachModal');
  const questionsContainer = document.getElementById('interviewQuestionsContainer');
  const summaryEl = document.getElementById('interviewExecutiveSummary');
  const toAskEl = document.getElementById('interviewQuestionsToAsk');
  const tipsEl = document.getElementById('interviewInsiderTips');
  const titleEl = document.getElementById('interviewCoachTitle');
  const subtitleEl = document.getElementById('interviewCoachSubtitle');

  modal.classList.remove('hidden');
  summaryEl.textContent = 'מייצר תדריך ראיונות מותאם אישית עם Google AI Pro...';
  questionsContainer.innerHTML = '<div class="text-xs text-slate-400 italic p-4 text-center">מנתח את דרישות המשרה מול קורות החיים של ליאור אזולאי...</div>';
  toAskEl.innerHTML = '';
  tipsEl.innerHTML = '';

  try {
    const res = await fetch(`/api/jobs/${jobId}/interview-prep`);
    if (!res.ok) throw new Error('Failed to fetch prep kit');
    const data = await res.json();

    titleEl.textContent = `מאמן ראיונות אישי: ${data.job_title || ''}`;
    subtitleEl.textContent = `הכנה ממוקדת עבור ראיון ב-${data.company || 'החברה'}`;
    summaryEl.textContent = data.executive_summary || '';

    // Questions & STAR answers
    const questions = data.top_questions || [];
    questionsContainer.innerHTML = questions.map((q, idx) => `
      <div class="p-4 rounded-xl border border-slate-200 bg-slate-50/60 space-y-2">
        <div class="flex items-center justify-between text-xs">
          <span class="font-bold text-purple-900 flex items-center gap-1.5">
            <span class="w-5 h-5 rounded-full bg-purple-600 text-white text-[10px] flex items-center justify-center font-bold">${idx + 1}</span>
            <span>${q.question}</span>
          </span>
          <span class="text-[10px] px-2 py-0.5 rounded-full bg-purple-100 text-purple-800 font-semibold">${q.category || 'מקצועי'}</span>
        </div>
        ${q.why_asked ? `<div class="text-[11px] text-slate-500 italic">💡 מטרת המראיין: ${q.why_asked}</div>` : ''}
        <div class="p-3 bg-white rounded-lg border border-purple-100 text-xs text-slate-800 leading-relaxed font-sans">
          <span class="font-bold text-purple-700 block mb-1">⭐ תשובת מודל מומלצת (בגוף ראשון):</span>
          ${q.star_answer}
        </div>
      </div>
    `).join('');

    // Questions to ask
    const toAsk = data.questions_to_ask_interviewer || [];
    toAskEl.innerHTML = toAsk.map(item => `<li>${item}</li>`).join('');

    // Tips
    const tips = data.insider_tips || [];
    tipsEl.innerHTML = tips.map(item => `<li>${item}</li>`).join('');

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error('Interview prep error:', err);
    summaryEl.textContent = 'שגיאה בטעינת מאמן הראיונות. נסה שוב מאוחר יותר.';
  }
}

function closeInterviewCoachModal() {
  document.getElementById('interviewCoachModal').classList.add('hidden');
}

// 2. WhatsApp Daily Digest
async function openWhatsAppModal() {
  const modal = document.getElementById('whatsappDigestModal');
  const textarea = document.getElementById('whatsappDigestTextarea');
  const directBtn = document.getElementById('btnSendWhatsAppDirect');

  modal.classList.remove('hidden');
  textarea.value = 'מפיק סיכום משרות מותאם לוואטסאפ...';

  try {
    const res = await fetch('/api/digest/whatsapp?min_score=70&limit=5');
    const data = await res.json();
    textarea.value = data.text || '';
    if (directBtn && data.whatsapp_url) {
      directBtn.href = data.whatsapp_url;
    }
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error('WhatsApp digest error:', err);
    textarea.value = 'שגיאה בהפקת סיכום וואטסאפ.';
  }
}

function closeWhatsAppModal() {
  document.getElementById('whatsappDigestModal').classList.add('hidden');
}

function copyWhatsAppDigestText() {
  const textarea = document.getElementById('whatsappDigestTextarea');
  const btn = document.getElementById('copyWhatsappBtnText');
  if (textarea) {
    navigator.clipboard.writeText(textarea.value).then(() => {
      const orig = btn.textContent;
      btn.textContent = 'הועתק בהצלחה! ✓';
      setTimeout(() => { btn.textContent = orig; }, 2000);
    });
  }
}

// 3. Skill Gaps & Roadmap
async function openSkillGapsModal() {
  const modal = document.getElementById('skillGapsModal');
  const summaryEl = document.getElementById('skillGapsSummaryBanner');
  const container = document.getElementById('skillGapsListContainer');

  modal.classList.remove('hidden');
  summaryEl.textContent = 'מנתח דרישות מעסיקים מתוך כל המשרות בבסיס הנתונים...';
  container.innerHTML = '<div class="text-xs text-slate-400 italic p-4 text-center">טוען נתונים...</div>';

  try {
    const res = await fetch('/api/insights/skill-gaps');
    const data = await res.json();

    summaryEl.textContent = data.recommendation_summary || '';
    const gaps = data.top_gaps || [];

    container.innerHTML = gaps.map((g, idx) => `
      <div class="p-4 rounded-xl border border-slate-200 bg-slate-50/70 space-y-2 hover:border-purple-300 transition">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="w-6 h-6 rounded-lg bg-purple-600 text-white text-xs font-bold flex items-center justify-center">${idx + 1}</span>
            <h5 class="text-xs font-bold text-slate-900">${g.skill}</h5>
          </div>
          <span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-100 text-purple-800 border border-purple-200">
            נדרש ב-${g.demand_percentage} ממשרות היעד
          </span>
        </div>
        <p class="text-xs text-slate-600 leading-relaxed">${g.description}</p>
        <div class="flex items-center justify-between pt-1">
          <span class="text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200">
            השפעה: ${g.impact}
          </span>
          <a href="${g.course_url}" target="_blank" class="text-xs font-semibold text-brand-600 hover:text-brand-700 hover:underline inline-flex items-center gap-1">
            <span>${g.course_name}</span>
            <i data-lucide="external-link" class="w-3 h-3"></i>
          </a>
        </div>
      </div>
    `).join('');

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error('Skill gaps error:', err);
    summaryEl.textContent = 'שגיאה בניתוח פערי כישורים.';
  }
}

function closeSkillGapsModal() {
  document.getElementById('skillGapsModal').classList.add('hidden');
}






// ==========================================
// Survey Agent (Polyeda & Gmail) Handlers
// ==========================================

let activeSurveyTab = 'surveys';

function openSurveyAgentModal() {
  const modal = document.getElementById('surveyAgentModal');
  if (modal) modal.classList.remove('hidden');
  loadSurveyStatus();
  loadSurveysList();
  if (window.lucide) lucide.createIcons();
}

function closeSurveyAgentModal() {
  const modal = document.getElementById('surveyAgentModal');
  if (modal) modal.classList.add('hidden');
}

function switchSurveyTab(tabName) {
  activeSurveyTab = tabName;
  const tabs = ['surveys', 'settings', 'profile'];
  tabs.forEach(t => {
    const btn = document.getElementById('tabBtn' + t.charAt(0).toUpperCase() + t.slice(1));
    const panel = document.getElementById('surveyPanel' + t.charAt(0).toUpperCase() + t.slice(1));
    if (t === tabName) {
      if (btn) {
        btn.classList.add('border-amber-600', 'text-amber-700');
        btn.classList.remove('border-transparent', 'text-slate-500');
      }
      if (panel) panel.classList.remove('hidden');
    } else {
      if (btn) {
        btn.classList.remove('border-amber-600', 'text-amber-700');
        btn.classList.add('border-transparent', 'text-slate-500');
      }
      if (panel) panel.classList.add('hidden');
    }
  });
  if (window.lucide) lucide.createIcons();
}

async function loadSurveyStatus() {
  try {
    const res = await fetch('/api/surveys/status');
    const data = await res.json();
    if (!data) return;

    const summary = data.summary || {};
    const totalPoints = summary.total_points || 0;
    const completedCount = summary.completed || 0;
    const totalSurveys = summary.total || 0;

    // Badges & Counters
    const pointsBadge = document.getElementById('surveyNavPointsBadge');
    if (pointsBadge) pointsBadge.textContent = `${totalPoints} נק'`;

    const totalPointsEl = document.getElementById('surveyTotalPoints');
    if (totalPointsEl) totalPointsEl.textContent = `${totalPoints} נק'`;

    const completedEl = document.getElementById('surveyCompletedCount');
    if (completedEl) completedEl.textContent = completedCount;

    const listBadge = document.getElementById('surveyListCountBadge');
    if (listBadge) listBadge.textContent = totalSurveys;

    // Gmail connection badge
    const gmailBadge = document.getElementById('surveyGmailStatusBadge');
    if (gmailBadge) {
      if (data.is_configured) {
        gmailBadge.className = 'px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200';
        gmailBadge.textContent = 'מחובר (מוגדר)';
      } else {
        gmailBadge.className = 'px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 border border-rose-200';
        gmailBadge.textContent = 'לא מוגדר';
      }
    }

    // Populate Settings inputs if empty
    const emailInput = document.getElementById('surveyGmailUserInput');
    if (emailInput && !emailInput.value && data.gmail_user) {
      emailInput.value = data.gmail_user;
    }
    const senderInput = document.getElementById('surveyTargetSenderInput');
    if (senderInput && data.target_sender) {
      senderInput.value = data.target_sender;
    }
    const headlessCheck = document.getElementById('surveyHeadlessCheckbox');
    if (headlessCheck && data.headless !== undefined) {
      headlessCheck.checked = !!data.headless;
    }

    // Populate profile inputs
    if (data.profile) {
      populateProfileInputs(data.profile);
    }
  } catch (err) {
    console.error('Failed to load survey status:', err);
  }
}

function populateProfileInputs(p) {
  if (!p) return;
  if (document.getElementById('profFullName')) document.getElementById('profFullName').value = p.full_name || '';
  if (document.getElementById('profGender')) document.getElementById('profGender').value = p.gender || 'נקבה';
  if (document.getElementById('profBirthYear')) document.getElementById('profBirthYear').value = p.birth_year || 1999;
  if (document.getElementById('profCity')) document.getElementById('profCity').value = p.city || 'תל אביב - יפו';
  if (document.getElementById('profDistrict')) document.getElementById('profDistrict').value = p.district || 'מרכז / תל אביב';
  if (document.getElementById('profMarital')) document.getElementById('profMarital').value = p.marital_status || 'רווקה';
  if (document.getElementById('profEducation')) document.getElementById('profEducation').value = p.education || 'תואר ראשון (.B.A)';
  if (document.getElementById('profEmployment')) document.getElementById('profEmployment').value = p.employment_status || 'שכירה במשרה מלאה';
  if (document.getElementById('profIncome')) document.getElementById('profIncome').value = p.monthly_income || 'ממוצעת (18,000 - 22,000 ₪)';
  if (document.getElementById('profReligion')) document.getElementById('profReligion').value = p.religion_sector || p.religion_level || 'חילונית';
}

async function loadSurveysList() {
  const container = document.getElementById('surveyFeedContainer');
  if (!container) return;

  try {
    const res = await fetch('/api/surveys/list');
    const data = await res.json();
    const surveys = Array.isArray(data) ? data : (data.surveys || []);

    if (surveys.length === 0) {
      container.innerHTML = `
        <div class="text-xs text-slate-500 italic p-6 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200 space-y-1">
          <p class="font-semibold text-slate-700">עדיין לא זוהו סקרים מ-panelview@polyeda.com</p>
          <p class="text-[11px] text-slate-400">ודא שהגדרת את פרטי ה-Gmail בלשונית ההגדרות ולחץ על "בדוק מיילים והפעל סוכן", או הדבק קישור ישיר למעלה.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = surveys.map(s => {
      const pts = s.reward_points !== undefined ? s.reward_points : (s.points_reward || 0);
      let statusBadge = '';
      if (s.status === 'completed') {
        statusBadge = `<span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">הושלם בהצלחה (+${pts} נק')</span>`;
      } else if (s.status === 'screened_out') {
        statusBadge = '<span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200">הסקר נסגר / מכסה מלאה</span>';
      } else if (s.status === 'running' || s.status === 'in_progress') {
        statusBadge = '<span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 border border-blue-200 animate-pulse">בתהליך מענה Playwright...</span>';
      } else if (s.status === 'failed') {
        statusBadge = '<span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 border border-rose-200">נכשל / שגיאה</span>';
      } else {
        statusBadge = '<span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">ממתין להרצה</span>';
      }

      const cleanScreenshot = s.screenshot_path ? s.screenshot_path.replace(/\\/g, '/').split('/').pop() : '';
      const screenshotBtn = cleanScreenshot ? `
        <a href="/static/survey_screenshots/${cleanScreenshot}" target="_blank" class="inline-flex items-center gap-1 text-[11px] font-semibold text-brand-600 hover:text-brand-700 hover:underline">
          <i data-lucide="image" class="w-3.5 h-3.5"></i>
          <span>צילום מסך הוכחה</span>
        </a>
      ` : '';

      return `
        <div class="p-3.5 rounded-xl border border-slate-200 bg-white hover:border-amber-300 transition shadow-2xs space-y-2">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="w-6 h-6 rounded-lg bg-amber-500/10 text-amber-800 text-xs font-bold flex items-center justify-center">#${s.id}</span>
              <h5 class="text-xs font-bold text-slate-900 truncate max-w-sm" title="${s.subject || ''}">
                ${s.subject || 'סקר ללא כותרת'}
              </h5>
            </div>
            ${statusBadge}
          </div>

          <div class="text-[11px] text-slate-500 flex items-center gap-3">
            <span>תאריך זיהוי: ${s.received_at ? new Date(s.received_at).toLocaleString('he-IL') : 'לא ידוע'}</span>
            <span>גמול: <strong>${pts} נקודות</strong></span>
          </div>

          ${s.error_message ? `<p class="text-[11px] text-rose-600 bg-rose-50 p-1.5 rounded-md border border-rose-100">הערה: ${s.error_message}</p>` : ''}

          <div class="flex items-center justify-between pt-1 border-t border-slate-100">
            <div class="flex items-center gap-3">
              <a href="${s.survey_url}" target="_blank" class="text-[11px] text-slate-500 hover:text-slate-800 hover:underline inline-flex items-center gap-1 truncate max-w-xs">
                <span>פתח קישור מקורי</span>
                <i data-lucide="external-link" class="w-3 h-3"></i>
              </a>
              ${screenshotBtn}
            </div>

            <button onclick="runSolverOnUrl('${encodeURIComponent(s.survey_url)}')" class="px-2.5 py-1 text-[11px] font-bold text-amber-900 bg-amber-100 hover:bg-amber-200 rounded-md transition active:scale-95 inline-flex items-center gap-1">
              <i data-lucide="play" class="w-3 h-3"></i>
              <span>הפעל שוב סוכן</span>
            </button>
          </div>
        </div>
      `;
    }).join('');

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error('Failed to load surveys list:', err);
  }
}

async function triggerSurveyCheck() {
  const spin = document.getElementById('surveyCheckSpin');
  const btnText = document.getElementById('btnSurveyCheckText');
  if (spin) spin.classList.add('animate-spin');
  if (btnText) btnText.textContent = 'בודק וממלא סקרים...';

  try {
    const res = await fetch('/api/surveys/check', { method: 'POST' });
    const data = await res.json();
    if (data.status === 'started' || data.status === 'success') {
      showToast('סוכן הסקרים רץ כעת ברקע! בודק את Gmail וממלא סקרים.', 'success');
      setTimeout(() => {
        loadSurveyStatus();
        loadSurveysList();
      }, 3000);
    } else {
      showToast(data.message || 'לא ניתן היה להפעיל את הסוכן', 'error');
    }
  } catch (err) {
    console.error('Trigger survey check error:', err);
    showToast('שגיאה בהפעלת בדיקת סקרים', 'error');
  } finally {
    if (spin) spin.classList.remove('animate-spin');
    if (btnText) btnText.textContent = 'בדוק מיילים והפעל סוכן עכשיו';
  }
}

async function submitDirectSurveyUrl() {
  const input = document.getElementById('directSurveyUrlInput');
  const url = input ? input.value.trim() : '';
  if (!url) {
    showToast('נא להזין קישור לסקר', 'warning');
    return;
  }

  showToast('הסוכן מתחיל כעת למלא את הסקר באמצעות Playwright...', 'info');

  try {
    const res = await fetch('/api/surveys/solve-url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url, headless: false })
    });
    const data = await res.json();
    if (data.status === 'started' || data.status === 'success') {
      showToast('סוכן Playwright הופעל בהצלחה עבור הקישור!', 'success');
      if (input) input.value = '';
      setTimeout(() => {
        loadSurveyStatus();
        loadSurveysList();
      }, 3000);
    } else {
      showToast(data.message || 'שגיאה בהפעלת הסוכן', 'error');
    }
  } catch (err) {
    console.error('Submit direct URL error:', err);
    showToast('שגיאה בחיבור לשרת', 'error');
  }
}

async function runSolverOnUrl(encodedUrl) {
  const url = decodeURIComponent(encodedUrl);
  showToast('הסוכן מתחיל כעת מענה חוזר על הסקר...', 'info');
  try {
    const res = await fetch('/api/surveys/solve-url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url, headless: false })
    });
    const data = await res.json();
    if (data.status === 'started' || data.status === 'success') {
      showToast('הסוכן התחיל לרוץ ברקע!', 'success');
      setTimeout(() => {
        loadSurveysList();
      }, 3000);
    }
  } catch (err) {
    showToast('שגיאה בהפעלת הסוכן', 'error');
  }
}

async function saveSurveySettings() {
  const gmail_user = document.getElementById('surveyGmailUserInput').value.trim();
  const gmail_app_password = document.getElementById('surveyGmailAppPwdInput').value.trim();
  const target_sender = document.getElementById('surveyTargetSenderInput').value.trim();
  const headless = document.getElementById('surveyHeadlessCheckbox').checked;

  try {
    const res = await fetch('/api/surveys/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        gmail_user,
        gmail_app_password,
        target_sender,
        headless
      })
    });
    const data = await res.json();
    if (data.status === 'ok' || data.status === 'success') {
      showToast('הגדרות Gmail נשמרו בהצלחה!', 'success');
      loadSurveyStatus();
    } else {
      showToast(data.message || 'שגיאה בשמירת הגדרות', 'error');
    }
  } catch (err) {
    console.error('Save survey settings error:', err);
    showToast('שגיאה בשמירת הגדרות', 'error');
  }
}

async function saveSurveyProfile() {
  const profile = {
    full_name: document.getElementById('profFullName').value.trim(),
    gender: document.getElementById('profGender').value,
    birth_year: parseInt(document.getElementById('profBirthYear').value) || 1999,
    city: document.getElementById('profCity').value.trim(),
    district: document.getElementById('profDistrict').value.trim(),
    marital_status: document.getElementById('profMarital').value,
    education: document.getElementById('profEducation').value.trim(),
    employment_status: document.getElementById('profEmployment').value.trim(),
    monthly_income: document.getElementById('profIncome').value.trim(),
    religion_sector: document.getElementById('profReligion').value
  };

  try {
    const res = await fetch('/api/surveys/profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile)
    });
    const data = await res.json();
    if (data.status === 'ok' || data.status === 'success') {
      showToast('פרופיל דמוגרפי לסקרים עודכן בהצלחה!', 'success');
      loadSurveyStatus();
    } else {
      showToast(data.message || 'שגיאה בעדכון פרופיל', 'error');
    }
  } catch (err) {
    console.error('Save survey profile error:', err);
    showToast('שגיאה בשמירת פרופיל', 'error');
  }
}

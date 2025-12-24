frappe.pages['visit-calendar'].on_page_load = function(wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __('Visit Calendar'),
    single_column: true
  });

  const $container = $(`
    <div class="visit-cal-wrap">
      <div class="visit-cal-toolbar">
        <div class="vc-row">
          <div class="vc-field">
            <label>${__('Month')}</label>
            <input type="month" class="form-control vc-month" />
          </div>

          <div class="vc-field">
            <label>${__('Salesman')}</label>
            <input type="text" class="form-control vc-salesman" placeholder="${__('User ID (optional)')}" />
          </div>

          <div class="vc-field">
            <label>${__('Journey Plan')}</label>
            <input type="text" class="form-control vc-journey-plan" placeholder="${__('Template name (optional)')}" />
          </div>

          <div class="vc-field">
            <label>${__('Poor Accuracy Threshold (m)')}</label>
            <input type="number" class="form-control vc-acc-th" value="50" />
          </div>

          <div class="vc-actions">
            <button class="btn btn-primary vc-load">${__('Load')}</button>
          </div>
        </div>
      </div>

      <div class="visit-cal-grid"></div>
    </div>
  `);

  page.main.append($container);

  // Default month = current
  const today = frappe.datetime.get_today();
  const ym = today.slice(0, 7); // YYYY-MM
  $container.find('.vc-month').val(ym);

  function getMonthDateValue() {
    const v = $container.find('.vc-month').val();
    if (!v) return null;
    return `${v}-01`;
  }

  // ✅ Build report route options (keep all filters)
  function buildDailyReportFilters(dateStr) {
    const salesman = ($container.find('.vc-salesman').val() || '').trim();
    const journey_plan = ($container.find('.vc-journey-plan').val() || '').trim();

    const opts = {
      view_mode: 'Detail',
      from_date: dateStr,
      to_date: dateStr
    };

    if (salesman) opts.salesman = salesman;
    if (journey_plan) opts.journey_plan = journey_plan;

    return opts;
  }

  // ✅ FIX #2: ALWAYS pass filters via frappe.route_options (ERPNext standard)
  function openDailyReport(dateStr) {
    frappe.route_options = buildDailyReportFilters(dateStr);
    frappe.set_route('query-report', 'Daily Visit Detail');
  }

  function renderCalendar(monthDate, apiDays) {
    const dt = new Date(monthDate);
    const year = dt.getFullYear();
    const month = dt.getMonth(); // 0-11

    const first = new Date(year, month, 1);
    const last = new Date(year, month + 1, 0);
    const daysInMonth = last.getDate();

    // Sunday-based grid
    const startDay = first.getDay(); // 0=Sun
    const weeks = Math.ceil((startDay + daysInMonth) / 7);

    const weekdayLabels = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];

    let html = `
      <div class="vc-month-title">${frappe.datetime.str_to_user(monthDate)} → ${frappe.datetime.obj_to_str(last)}</div>
      <table class="table table-bordered vc-table">
        <thead>
          <tr>${weekdayLabels.map(d => `<th>${d}</th>`).join('')}</tr>
        </thead>
        <tbody>
    `;

    let dayCounter = 1;
    for (let w = 0; w < weeks; w++) {
      html += '<tr>';

      for (let d = 0; d < 7; d++) {
        const cellIndex = w * 7 + d;

        if (cellIndex < startDay || dayCounter > daysInMonth) {
          html += `<td class="vc-empty"></td>`;
          continue;
        }

        const y = year;
        const m = (month + 1).toString().padStart(2, '0');
        const dd = dayCounter.toString().padStart(2, '0');
        const dateStr = `${y}-${m}-${dd}`;

        const info = apiDays[dateStr] || {};
        const planned = info.planned || 0;
        const completed = info.completed || 0;
        const missed = info.missed || 0;

        // ✅ FIX #1: show dash if no real accuracy (null/undefined/0)
        const avgAcc =
          (info.avg_accuracy_m === null || info.avg_accuracy_m === undefined || Number(info.avg_accuracy_m) <= 0)
            ? '—'
            : Number(info.avg_accuracy_m).toFixed(1);

        const badgeClass = missed > 0 ? 'vc-bad' : (planned > 0 ? 'vc-good' : 'vc-neutral');

        html += `
          <td class="vc-day" data-date="${dateStr}">
            <div class="vc-day-top">
              <div class="vc-day-num">${dayCounter}</div>
              <div class="vc-badge ${badgeClass}">
                ${planned > 0 ? `${__('Planned')}: ${planned}` : __('No Plan')}
              </div>
            </div>

            <div class="vc-stats">
              <div>${__('Completed')}: <span class="vc-completed">${completed}</span></div>
              <div>${__('Missed')}: <span class="vc-missed">${missed}</span></div>
              <div>${__('Avg Acc')}: <span class="vc-acc">${avgAcc}</span></div>
            </div>

            <div class="vc-actions-row">
              <button class="btn btn-xs btn-default vc-open">${__('Open Detail')}</button>
            </div>
          </td>
        `;

        dayCounter++;
      }

      html += '</tr>';
    }

    html += `
        </tbody>
      </table>
      <div class="vc-hint">
        ${__('Tip: Click any day to open Daily Visit Detail report for that date with same filters.')}
      </div>
    `;

    const $grid = $container.find('.visit-cal-grid');
    $grid.html(html);

    // ✅ click any day
    $grid.find('.vc-day').on('click', function(e) {
      if ($(e.target).hasClass('vc-open')) return;
      const dateStr = $(this).data('date');
      openDailyReport(dateStr);
    });

    $grid.find('.vc-open').on('click', function(e) {
      e.stopPropagation();
      const dateStr = $(this).closest('.vc-day').data('date');
      openDailyReport(dateStr);
    });
  }

  function loadCalendar() {
    const monthDate = getMonthDateValue();
    if (!monthDate) {
      frappe.msgprint(__('Please select a month.'));
      return;
    }

    const salesman = ($container.find('.vc-salesman').val() || '').trim() || null;
    const journey_plan = ($container.find('.vc-journey-plan').val() || '').trim() || null;
    const poor_accuracy_threshold = parseFloat($container.find('.vc-acc-th').val() || 50);

    frappe.call({
      method: 'salesman_journey.api.analytics.get_month_calendar',
      args: {
        month_date: monthDate,
        salesman: salesman,
        journey_plan: journey_plan,
        poor_accuracy_threshold: poor_accuracy_threshold
      },
      freeze: true,
      callback: function(r) {
        const out = r.message || {};
        const days = out.days || {};
        renderCalendar(monthDate, days);
      }
    });
  }

  $container.find('.vc-load').on('click', loadCalendar);
  loadCalendar();
};

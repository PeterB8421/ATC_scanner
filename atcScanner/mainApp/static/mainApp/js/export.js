const today = new Date();
let currentYear = today.getFullYear();
let currentMonth = today.getMonth() + 1;
let currentDay = null;

let activeFilterDate = null;

const calendarGrid = document.getElementById('calendar-grid');
const clearButton = document.getElementById('clear-date');
const dayExportButton = document.getElementById('dayExport');

const monthSelect = document.getElementById('month-select');
const yearSelect = document.getElementById('year-select');

const baseYear = today.getFullYear();
for (let y = baseYear; y >= 2000; y--) {
    const option = document.createElement('option');
    option.value = y;
    option.textContent = y;
    yearSelect.appendChild(option);
}

async function renderCalendar(year, month, selectedDay = null) {
    const grid = document.getElementById('calendar-grid');
    grid.innerHTML = ''; // Clear existing calendar

    document.getElementById('year-select').value = year;
    document.getElementById('month-select').value = month;

    // Fetch the counts from Django
    const paddedMonth = String(month).padStart(2, '0');
    const response = await fetch(`/api/month_counts?year=${year}&month=${paddedMonth}`);
    const countsData = await response.json();

    // If there are no recordings for selected month, disable the export button
    const totalRecordings = Object.values(countsData).reduce((sum, count) => sum + count, 0);
    const exportBtn = document.getElementById('monthExport');

    if (exportBtn) {
        if (totalRecordings === 0) {
            exportBtn.classList.add('disabled');
            exportBtn.disabled = true;
            exportBtn.setAttribute('aria-disabled', 'true');
        } else {
            exportBtn.classList.remove('disabled');
            exportBtn.removeAttribute('aria-disabled');
            exportBtn.disabled = false;
        }
    }

    // Add Day of Week Headers
    const daysOfWeek = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    daysOfWeek.forEach(day => {
        grid.innerHTML += `<div class="fw-bold text-muted">${day}</div>`;
    });

    let firstDayIndex = new Date(year, month - 1, 1).getDay();
    firstDayIndex = firstDayIndex === 0 ? 6 : firstDayIndex - 1;
    const daysInMonth = new Date(year, month, 0).getDate();

    // Pad the empty days before the 1st of the month
    for (let i = 0; i < firstDayIndex; i++) {
        grid.innerHTML += `<div class="cal-empty"></div>`;
    }

    // Build the actual days
    for (let day = 1; day <= daysInMonth; day++) {
        const paddedDay = String(day).padStart(2, '0');
        const dateString = `${year}-${paddedMonth}-${paddedDay}`;

        // Check if API returned a count for this specific date string
        const count = countsData[dateString] || 0;

        // If there are recordings, show a green badge. Otherwise, show nothing.
        const badgeHtml = count > 0
            ? `<br><span class="badge bg-success">${count}</span>`
            : '<br><span class="badge bg-secondary">0</span>';

        const highlightClass = (dateString === selectedDay) ? "bg-primary text-white" : "";
        const disabledClasses = (count === 0) ? "pe-none opacity-50" : "cursor-pointer";

        grid.innerHTML += `
            <div class="cal-day ${highlightClass} ${disabledClasses}" data-date="${dateString}" data-day="${paddedDay}">
                <strong>${day}</strong>
                ${badgeHtml}
            </div>
        `;
    }
}

// Button Listeners to change months
document.getElementById('prev-month').addEventListener('click', () => {
    currentMonth--;
    if (currentMonth < 1) { currentMonth = 12; currentYear--; }
    renderCalendar(currentYear, currentMonth);
});

document.getElementById('next-month').addEventListener('click', () => {
    currentMonth++;
    if (currentMonth > 12) { currentMonth = 1; currentYear++; }
    renderCalendar(currentYear, currentMonth);
});

calendarGrid.addEventListener('click', (event) => {
    const clickedDay = event.target.closest('.cal-day');
    if (!clickedDay) return;

    activeFilterDate = clickedDay.getAttribute('data-date');
    currentDay = clickedDay.getAttribute('data-day');
    document.getElementById('selected-day-message').style.display = "flex";
    document.getElementById('selectedDay').innerHTML = `${activeFilterDate}`;

    // Highlight the clicked day
    document.querySelectorAll('.cal-day').forEach(day => {
        day.classList.remove('bg-primary', 'text-white');
    });
    clickedDay.classList.add('bg-primary', 'text-white');

    // Show the "Clear Selection" button
    clearButton.style.display = 'block';
    dayExportButton.classList.remove('disabled');
    dayExportButton.disabled = false;
    dayExportButton.removeAttribute('aria-disabled');

});

// Update the Clear Button Listener
clearButton.addEventListener('click', () => {
    activeFilterDate = null;
    document.getElementById('selected-day-message').style.display = "none";

    // Remove highlight from all calendar days
    document.querySelectorAll('.cal-day').forEach(day => {
        day.classList.remove('bg-primary', 'text-white');
    });

    // Hide the clear button again
    clearButton.style.display = 'none';
    dayExportButton.classList.add('disabled');
    dayExportButton.disabled = true;
    dayExportButton.setAttribute('aria-disabled', 'true');
});

document.addEventListener('DOMContentLoaded', function() {
    const exportDayBtn = document.getElementById('dayExport');
    const messageContainer = document.getElementById('export-message-container');

    exportDayBtn.addEventListener('click', async function(event) {
        // Stop the browser from following the link
        event.preventDefault();

        // Clear old messages and show loading state
        messageContainer.innerHTML = '';
        const originalText = this.innerHTML;
        this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
        this.classList.add('disabled');

        try {
            if(!currentDay){
                throw new Error("Current day is not set!");
            }
            const selectedTime = document.getElementById('timeSelect').value;
            const url = new URL(this.dataset.url, window.location.origin);
            url.searchParams.append('year', currentYear.toString());
            url.searchParams.append('month', currentMonth.toString());
            url.searchParams.append('day', currentDay.toString());
            if(selectedTime !== ""){
                url.searchParams.append('hour', selectedTime);
            }
            // Send request to Django endpoint
            const response = await fetch(url);

            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }

            const data = await response.json();

            // Show success message
            messageContainer.innerHTML = `
                <div class="alert alert-success alert-dismissible fade show" role="alert">
                    <strong>Success!</strong> The archive named <b>${data.filename}</b> was created successfully.
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>`;
            loadFileList();

        } catch (error) {
            console.error("Archive creation failed:", error);

            // Show error message
            messageContainer.innerHTML = `
                <div class="alert alert-danger alert-dismissible fade show" role="alert">
                    <strong>Failed!</strong> There was an error creating the archive.
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>`;
        } finally {
            // Reset the button
            this.innerHTML = originalText;
            this.classList.remove('disabled');
        }
    });
});

// A reusable function to fetch and populate the table
async function loadFileList() {
    const messageContainer = document.getElementById('export-message-container');
    const tableBody = document.getElementById('export-table-content');

    try {
        const response = await fetch('/api/export/list_files');

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const data = await response.json();

        // The backend now sends an array of objects
        const files = data.files || [];

        tableBody.innerHTML = '';

        if (files.length === 0) {
            // Updated colspan to 3 to account for the new Size column
            tableBody.innerHTML = `
                <tr>
                    <td colspan="3" class="text-center text-muted py-3">
                        No export files found.
                    </td>
                </tr>`;
            return;
        }

        // Loop through the array of file objects
        files.forEach(file => {
            const row = document.createElement('tr');

            // Filename Column
            const nameCell = document.createElement('td');
            nameCell.textContent = file.filename;

            // Size Column
            const sizeCell = document.createElement('td');
            // Format the float with a label
            sizeCell.textContent = `${file.size_mb} MB`;

            // Actions Column
            const actionCell = document.createElement('td');
            actionCell.className = "text-end";

            // Download Button
            actionCell.innerHTML = `
                <a href="${file.path}" class="btn btn-sm btn-outline-primary" download="${file.filename}">
                    Download
                </a>
            `;

            // Delete Button
            const deleteBtn = document.createElement('button');
            deleteBtn.className = "btn btn-sm btn-outline-danger ms-2"; // ms-2 adds a little spacing between the buttons

            deleteBtn.dataset.url = `${window.location.origin}/export/delete?file=${encodeURIComponent(file.path)}`;
            deleteBtn.textContent = 'Delete';

            deleteBtn.addEventListener('click', async function(event) {
                event.preventDefault();

                const originalText = this.textContent;
                this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span>';
                this.disabled = true;

                try {
                    const response = await fetch(this.dataset.url);

                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.error || `Server error: ${response.status}`);
                    }

                    messageContainer.innerHTML = `
                    <div class="alert alert-success alert-dismissible fade show" role="alert">
                        <strong>Success!</strong> File was successfully deleted!
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>`;

                    // Reload the table
                    loadFileList();

                } catch (error) {
                    console.error("Delete failed:", error);
                    messageContainer.innerHTML = `
                    <div class="alert alert-danger alert-dismissible fade show" role="alert">
                        <strong>Error!</strong> ${error.message}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>`;

                    this.textContent = originalText;
                    this.disabled = false;
                }
            });

            // Append the delete button next to the download button
            actionCell.appendChild(deleteBtn);

            // Put the cells in the row
            row.appendChild(nameCell);
            row.appendChild(sizeCell);
            row.appendChild(actionCell);

            // Put the row in the table
            tableBody.appendChild(row);
        });

    } catch (error) {
        console.error("Failed to load file list:", error);

        tableBody.innerHTML = `
            <tr>
                <td colspan="3" class="text-center text-danger py-3">
                    Failed to load files. Please try again later.
                </td>
            </tr>`;
    }
}

// 6. Automatically run this function when the page first loads!
document.addEventListener('DOMContentLoaded', loadFileList);

renderCalendar(currentYear, currentMonth, activeFilterDate);

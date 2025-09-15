/**
 * Week Review JavaScript functionality
 */

let weekCounter = 0;
let weekPlans = [];

// Load existing week plans
function loadWeekPlans(plans) {
    const container = document.getElementById('weeklyPlanContainer');
    container.innerHTML = '';
    
    plans.forEach((plan, index) => {
        createWeekCard(plan, index + 1);
    });
    
    weekPlans = plans;
    updateWeekNumbers();
    
    if (plans.length === 0) {
        showEmptyState();
    }
}

// Show empty state
function showEmptyState() {
    document.getElementById('emptyState').style.display = 'block';
    document.getElementById('weeklyPlanContainer').innerHTML = '';
}

// Hide empty state
function hideEmptyState() {
    document.getElementById('emptyState').style.display = 'none';
}

// Create a new week card
function createWeekCard(weekData = null, weekNumber = null) {
    const template = document.getElementById('weekTemplate');
    const clone = template.cloneNode(true);
    
    const actualWeekNumber = weekNumber || (weekCounter + 1);
    weekCounter = Math.max(weekCounter, actualWeekNumber);
    
    // Set up the cloned card
    clone.id = `week_${actualWeekNumber}`;
    clone.style.display = 'block';
    clone.setAttribute('data-week', actualWeekNumber);
    
    // Set week number and title
    clone.querySelector('.week-number').textContent = actualWeekNumber;
    const titleInput = clone.querySelector('.week-title');
    titleInput.value = weekData ? weekData.title : `Week ${actualWeekNumber} Topic`;
    titleInput.setAttribute('data-week', actualWeekNumber);
    
    // Populate data if provided
    if (weekData) {
        populateWeekData(clone, weekData);
    } else {
        // Add default empty items
        addDefaultItems(clone);
    }
    
    // Add to container
    document.getElementById('weeklyPlanContainer').appendChild(clone);
    hideEmptyState();
    
    return clone;
}

// Populate week card with data
function populateWeekData(weekCard, weekData) {
    // Learning outcomes
    const loContainer = weekCard.querySelector('.learning-outcomes-container');
    weekData.learning_outcomes.forEach(lo => {
        addItemToContainer(loContainer, lo, 'learning-outcome');
    });
    
    // Lecture topics
    const topicsContainer = weekCard.querySelector('.lecture-topics-container');
    weekData.lecture_topics.forEach(topic => {
        addItemToContainer(topicsContainer, topic, 'lecture-topic');
    });
    
    // Tutorial activities
    const tutorialContainer = weekCard.querySelector('.tutorial-activities-container');
    weekData.tutorial_activities.forEach(activity => {
        addItemToContainer(tutorialContainer, activity, 'tutorial-activity');
    });
    
    // Lab activities
    const labContainer = weekCard.querySelector('.lab-activities-container');
    weekData.lab_activities.forEach(lab => {
        addItemToContainer(labContainer, lab, 'lab-activity');
    });
    
    // Readings
    const readingsContainer = weekCard.querySelector('.readings-container');
    weekData.readings.forEach(reading => {
        addItemToContainer(readingsContainer, reading, 'reading');
    });
    
    // Deliverables
    const deliverablesContainer = weekCard.querySelector('.deliverables-container');
    weekData.deliverables.forEach(deliverable => {
        addItemToContainer(deliverablesContainer, deliverable, 'deliverable');
    });
}

// Add default empty items to new week
function addDefaultItems(weekCard) {
    const containers = [
        { selector: '.learning-outcomes-container', type: 'learning-outcome', default: 'Learning Outcome' },
        { selector: '.lecture-topics-container', type: 'lecture-topic', default: 'Lecture Topic' },
        { selector: '.tutorial-activities-container', type: 'tutorial-activity', default: 'Tutorial Activity' }
    ];
    
    containers.forEach(container => {
        const element = weekCard.querySelector(container.selector);
        addItemToContainer(element, container.default, container.type);
    });
}

// Add item to container
function addItemToContainer(container, value, type) {
    const itemDiv = document.createElement('div');
    itemDiv.className = 'input-group mb-2';
    itemDiv.innerHTML = `
        <input type="text" class="form-control ${type}" value="${value}" 
               placeholder="Enter ${type.replace('-', ' ')}">
        <button class="btn btn-outline-danger btn-sm" onclick="removeItem(this)" type="button">
            <i class="fas fa-times"></i>
        </button>
    `;
    container.appendChild(itemDiv);
}

// Remove item
function removeItem(button) {
    button.closest('.input-group').remove();
}

// Toggle week details
function toggleWeekDetails(button) {
    const weekCard = button.closest('.week-card');
    const details = weekCard.querySelector('.week-details');
    const icon = button.querySelector('i');
    
    if (details.classList.contains('show')) {
        details.classList.remove('show');
        icon.className = 'fas fa-edit';
        button.innerHTML = '<i class="fas fa-edit"></i> Edit';
    } else {
        details.classList.add('show');
        icon.className = 'fas fa-eye-slash';
        button.innerHTML = '<i class="fas fa-eye-slash"></i> Hide';
    }
}

// Add new week
function addNewWeek() {
    const newWeek = createWeekCard();
    newWeek.scrollIntoView({ behavior: 'smooth' });
    
    // Auto-open the details for the new week
    const editButton = newWeek.querySelector('.btn-outline-primary');
    toggleWeekDetails(editButton);
}

// Delete week
function deleteWeek(button) {
    if (confirm('Are you sure you want to delete this week?')) {
        const weekCard = button.closest('.week-card');
        weekCard.remove();
        updateWeekNumbers();
        
        // Show empty state if no weeks left
        const remainingWeeks = document.querySelectorAll('.week-card');
        if (remainingWeeks.length === 0) {
            showEmptyState();
        }
    }
}

// Update week numbers after deletion or reordering
function updateWeekNumbers() {
    const weekCards = document.querySelectorAll('.week-card');
    weekCards.forEach((card, index) => {
        const weekNumber = index + 1;
        card.setAttribute('data-week', weekNumber);
        card.querySelector('.week-number').textContent = weekNumber;
        card.querySelector('.week-title').setAttribute('data-week', weekNumber);
        card.id = `week_${weekNumber}`;
    });
    weekCounter = weekCards.length;
}

// Add specific items
function addLearningOutcome(button) {
    const container = button.parentElement.querySelector('.learning-outcomes-container');
    addItemToContainer(container, '', 'learning-outcome');
}

function addLectureTopic(button) {
    const container = button.parentElement.querySelector('.lecture-topics-container');
    addItemToContainer(container, '', 'lecture-topic');
}

function addTutorialActivity(button) {
    const container = button.parentElement.querySelector('.tutorial-activities-container');
    addItemToContainer(container, '', 'tutorial-activity');
}

function addLabActivity(button) {
    const container = button.parentElement.querySelector('.lab-activities-container');
    addItemToContainer(container, '', 'lab-activity');
}

function addReading(button) {
    const container = button.parentElement.querySelector('.readings-container');
    addItemToContainer(container, '', 'reading');
}

function addDeliverable(button) {
    const container = button.parentElement.querySelector('.deliverables-container');
    addItemToContainer(container, '', 'deliverable');
}

// Generate weekly plan
async function generatePlan() {
    const loadingIndicator = document.getElementById('loadingIndicator');
    loadingIndicator.style.display = 'block';
    
    try {
        const response = await fetch('/api/generate-plan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `session_id=${sessionId}`
        });
        
        const result = await response.json();
        
        if (response.ok) {
            loadWeekPlans(result.week_plans);
        } else {
            throw new Error(result.detail || 'Failed to generate plan');
        }
    } catch (error) {
        alert('Error generating plan: ' + error.message);
    } finally {
        loadingIndicator.style.display = 'none';
    }
}

// Collect current week plan data
function collectWeekPlans() {
    const weekCards = document.querySelectorAll('.week-card');
    const plans = [];
    
    weekCards.forEach((card, index) => {
        const weekNumber = index + 1;
        const title = card.querySelector('.week-title').value;
        
        const plan = {
            week_number: weekNumber,
            title: title,
            learning_outcomes: collectInputValues(card, '.learning-outcome'),
            lecture_topics: collectInputValues(card, '.lecture-topic'),
            tutorial_activities: collectInputValues(card, '.tutorial-activity'),
            lab_activities: collectInputValues(card, '.lab-activity'),
            readings: collectInputValues(card, '.reading'),
            deliverables: collectInputValues(card, '.deliverable')
        };
        
        plans.push(plan);
    });
    
    return plans;
}

// Collect input values from container
function collectInputValues(container, selector) {
    const inputs = container.querySelectorAll(selector);
    return Array.from(inputs).map(input => input.value).filter(value => value.trim() !== '');
}

// Approve plan and proceed
async function approvePlan() {
    const plans = collectWeekPlans();
    
    if (plans.length === 0) {
        alert('Please add at least one week to the plan.');
        return;
    }
    
    try {
        const response = await fetch('/api/approve-plan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `session_id=${sessionId}&approved_weeks=${encodeURIComponent(JSON.stringify(plans))}`
        });
        
        const result = await response.json();
        
        if (response.ok) {
            // Redirect to content generation page
            window.location.href = `/content-generation/${sessionId}`;
        } else {
            throw new Error(result.detail || 'Failed to approve plan');
        }
    } catch (error) {
        alert('Error approving plan: ' + error.message);
    }
}

// Generate content for specific week
async function generateWeekContent(button) {
    const weekCard = button.closest('.week-card');
    const weekNumber = parseInt(weekCard.getAttribute('data-week'));
    const statusSpan = weekCard.querySelector('.generation-status');
    
    // Get selected content types
    const contentTypes = [];
    const checkboxes = weekCard.querySelectorAll('.form-check-input:checked');
    checkboxes.forEach(checkbox => {
        contentTypes.push(checkbox.id);
    });
    
    if (contentTypes.length === 0) {
        alert('Please select at least one content type to generate.');
        return;
    }
    
    // Disable button and show progress
    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Generating...';
    statusSpan.innerHTML = '<i class="fas fa-spinner fa-spin text-primary"></i> Generating content...';
    
    try {
        const weekPlan = collectWeekPlan(weekCard, weekNumber);
        
        const response = await fetch('/api/generate-week-content', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: sessionId,
                week_plan: weekPlan,
                content_types: contentTypes
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            statusSpan.innerHTML = '<i class="fas fa-check text-success"></i> Content generated successfully!';
            
            // Show preview/edit button
            const previewBtn = document.createElement('button');
            previewBtn.className = 'btn btn-outline-info btn-sm ms-2';
            previewBtn.innerHTML = '<i class="fas fa-eye me-1"></i>Preview';
            previewBtn.onclick = () => previewWeekContent(weekNumber);
            weekCard.querySelector('.content-generation-section .mt-3').appendChild(previewBtn);
            
        } else {
            throw new Error(result.detail || 'Failed to generate content');
        }
    } catch (error) {
        statusSpan.innerHTML = '<i class="fas fa-exclamation-triangle text-danger"></i> Error: ' + error.message;
    } finally {
        button.disabled = false;
        button.innerHTML = '<i class="fas fa-play me-2"></i>Generate Content for This Week';
    }
}

// Collect single week plan data
function collectWeekPlan(weekCard, weekNumber) {
    return {
        week_number: weekNumber,
        title: weekCard.querySelector('.week-title').value,
        learning_outcomes: collectInputValues(weekCard, '.learning-outcome'),
        lecture_topics: collectInputValues(weekCard, '.lecture-topic'),
        tutorial_activities: collectInputValues(weekCard, '.tutorial-activity'),
        lab_activities: collectInputValues(weekCard, '.lab-activity'),
        readings: collectInputValues(weekCard, '.reading'),
        deliverables: collectInputValues(weekCard, '.deliverable')
    };
}

// Preview week content
function previewWeekContent(weekNumber) {
    window.open(`/preview-week-content/${sessionId}/${weekNumber}`, '_blank');
}
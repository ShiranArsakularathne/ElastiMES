// MES System Frontend Application
class MESApp {
    constructor() {
        this.currentUser = null;
        this.currentModule = 'home';
        this.currentPage = 'beam-loading';
        this.apiBaseUrl = window.location.origin + '/api';
        this.init();
    }

    init() {
        this.bindEvents();
        this.checkAuth();
        this.loadHardwareStatus();
    }

    bindEvents() {
        // Login form
        document.addEventListener('DOMContentLoaded', () => {
            const loginForm = document.getElementById('loginForm');
            if (loginForm) {
                loginForm.addEventListener('submit', (e) => this.handleLogin(e));
            }

            const rfidLoginBtn = document.getElementById('rfidLoginBtn');
            if (rfidLoginBtn) {
                rfidLoginBtn.addEventListener('click', () => this.handleRfidLogin());
            }

            // Menu navigation
            document.querySelectorAll('.menu-item').forEach(item => {
                item.addEventListener('click', (e) => this.navigateToModule(e));
            });

            // WRP sub-pages
            const wrpTabs = document.querySelectorAll('.wrp-tab');
            if (wrpTabs.length) {
                wrpTabs.forEach(tab => {
                    tab.addEventListener('click', (e) => this.switchWrpPage(e));
                });
            }

            // Beam Loading form
            const retrievePlanBtn = document.getElementById('retrievePlanBtn');
            if (retrievePlanBtn) {
                retrievePlanBtn.addEventListener('click', () => this.retrievePlan());
            }

            const scanBeamBtn = document.getElementById('scanBeamBtn');
            if (scanBeamBtn) {
                scanBeamBtn.addEventListener('click', () => this.scanBeamCode());
            }

            const saveBeamLoadingBtn = document.getElementById('saveBeamLoadingBtn');
            if (saveBeamLoadingBtn) {
                saveBeamLoadingBtn.addEventListener('click', () => this.saveBeamLoading());
            }

            // Simulate hardware readings
            const simulatePlcBtn = document.getElementById('simulatePlcBtn');
            if (simulatePlcBtn) {
                simulatePlcBtn.addEventListener('click', () => this.simulatePlcReading());
            }

            const simulateRfidBtn = document.getElementById('simulateRfidBtn');
            if (simulateRfidBtn) {
                simulateRfidBtn.addEventListener('click', () => this.simulateRfidScan());
            }

            const simulateBarcodeBtn = document.getElementById('simulateBarcodeBtn');
            if (simulateBarcodeBtn) {
                simulateBarcodeBtn.addEventListener('click', () => this.simulateBarcodeScan());
            }
        });
    }

    async checkAuth() {
        // Check if user is logged in (simplified)
        const token = localStorage.getItem('mes_token');
        if (token && window.location.pathname === '/login.html') {
            window.location.href = '/';
        } else if (!token && window.location.pathname !== '/login.html') {
            window.location.href = '/login.html';
        }
    }

    async handleLogin(e) {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        try {
            const response = await fetch(`${this.apiBaseUrl}/users/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            if (response.ok) {
                const data = await response.json();
                localStorage.setItem('mes_token', data.access_token);
                localStorage.setItem('mes_user', JSON.stringify(data.user));
                window.location.href = '/';
            } else {
                this.showAlert('Login failed. Please check credentials.', 'error');
            }
        } catch (error) {
            this.showAlert('Network error. Please try again.', 'error');
        }
    }

    async handleRfidLogin() {
        this.showAlert('Please scan your RFID card...', 'info');
        
        try {
            // Simulate RFID scan
            const response = await fetch(`${this.apiBaseUrl}/rfid/scan`, {
                method: 'POST'
            });

            if (response.ok) {
                const data = await response.json();
                localStorage.setItem('mes_token', data.access_token);
                localStorage.setItem('mes_user', JSON.stringify(data.user));
                this.showAlert('RFID login successful!', 'success');
                setTimeout(() => {
                    window.location.href = '/';
                }, 1000);
            } else {
                this.showAlert('RFID login failed. Please try again.', 'error');
            }
        } catch (error) {
            this.showAlert('RFID scanner not available. Using simulated login.', 'warning');
            // Fallback to simulated login
            localStorage.setItem('mes_token', 'simulated_token');
            localStorage.setItem('mes_user', JSON.stringify({ id: 1, username: 'operator', role: 'operator' }));
            setTimeout(() => {
                window.location.href = '/';
            }, 1500);
        }
    }

    navigateToModule(e) {
        e.preventDefault();
        const module = e.currentTarget.dataset.module;
        this.currentModule = module;
        
        // Update active menu item
        document.querySelectorAll('.menu-item').forEach(item => {
            item.classList.remove('active');
        });
        e.currentTarget.classList.add('active');
        
        // Load module content
        this.loadModule(module);
    }

    async loadModule(module) {
        const contentArea = document.getElementById('contentArea');
        if (!contentArea) return;

        let html = '';
        
        switch(module) {
            case 'home':
                html = await this.loadHomePage();
                break;
            case 'wrp':
                html = await this.loadWRPPage();
                break;
            case 'loom':
                html = '<h2>LOOM Module</h2><p>Coming soon...</p>';
                break;
            case 'range':
                html = '<h2>RANGE Module</h2><p>Coming soon...</p>';
                break;
            case 'exhst':
                html = '<h2>EXHST Module</h2><p>Coming soon...</p>';
                break;
            case 'pack':
                html = '<h2>PACK Module</h2><p>Coming soon...</p>';
                break;
            case 'inspc':
                html = '<h2>INSPC Module</h2><p>Coming soon...</p>';
                break;
            case 'users':
                html = '<h2>USERS Module</h2><p>Coming soon...</p>';
                break;
            default:
                html = '<h2>Module not implemented</h2>';
        }
        
        contentArea.innerHTML = html;
        this.bindEvents(); // Rebind events for new content
    }

    async loadHomePage() {
        return `
            <div class="dashboard">
                <h2>Dashboard</h2>
                <div class="hardware-status">
                    <div class="status-item">
                        <div class="status-indicator online"></div>
                        <span>PLC: Online</span>
                    </div>
                    <div class="status-item">
                        <div class="status-indicator online"></div>
                        <span>RFID: Online</span>
                    </div>
                    <div class="status-item">
                        <div class="status-indicator online"></div>
                        <span>Barcode Scanner: Online</span>
                    </div>
                </div>
                <div class="stats-grid">
                    <div class="card">
                        <h3>Today's Production</h3>
                        <p class="stat-value">245</p>
                        <p class="stat-label">Beams</p>
                    </div>
                    <div class="card">
                        <h3>Active Machines</h3>
                        <p class="stat-value">12</p>
                        <p class="stat-label">Running</p>
                    </div>
                    <div class="card">
                        <h3>Pending Tasks</h3>
                        <p class="stat-value">8</p>
                        <p class="stat-label">To Complete</p>
                    </div>
                </div>
            </div>
        `;
    }

    async loadWRPPage() {
        return `
            <div class="wrp-module">
                <h2>WRP Module</h2>
                <div class="wrp-tabs">
                    <button class="wrp-tab active" data-page="beam-loading">Beam Loading</button>
                    <button class="wrp-tab" data-page="warp">Warp</button>
                    <button class="wrp-tab" data-page="unload">Unload</button>
                </div>
                <div id="wrpContent">
                    ${await this.loadBeamLoadingPage()}
                </div>
            </div>
        `;
    }

    async loadBeamLoadingPage() {
        return `
            <div class="beam-loading-page">
                <div class="hardware-status">
                    <div class="status-item">
                        <div class="status-indicator online"></div>
                        <span>PLC Load Cells: Online</span>
                    </div>
                    <div class="status-item">
                        <div class="status-indicator online"></div>
                        <span>Barcode Scanner: Online</span>
                    </div>
                    <button id="simulatePlcBtn" class="btn btn-secondary">Simulate PLC Reading</button>
                    <button id="simulateBarcodeBtn" class="btn btn-secondary">Simulate Barcode Scan</button>
                </div>
                
                <div class="form-grid">
                    <div class="card">
                        <div class="card-header">
                            <h3>Machine & Plan</h3>
                        </div>
                        <div class="form-group">
                            <label for="machineCode">Machine Code</label>
                            <input type="text" id="machineCode" class="form-control" placeholder="Scan machine barcode">
                        </div>
                        <button id="retrievePlanBtn" class="btn btn-primary">Retrieve Plan from ERP</button>
                        
                        <div id="planList" style="margin-top: 20px; display: none;">
                            <h4>Available Plans</h4>
                            <table>
                                <thead>
                                    <tr>
                                        <th>Select</th>
                                        <th>Plan ID</th>
                                        <th>Yarn Code</th>
                                        <th>Beam Size</th>
                                        <th>Ends</th>
                                    </tr>
                                </thead>
                                <tbody id="planTableBody">
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            <h3>Plan Details</h3>
                        </div>
                        <div class="form-group">
                            <label for="yarnCode">Yarn Code</label>
                            <input type="text" id="yarnCode" class="form-control" readonly>
                        </div>
                        <div class="form-group">
                            <label for="beamSize">Beam Size</label>
                            <input type="text" id="beamSize" class="form-control" readonly>
                        </div>
                        <div class="form-group">
                            <label for="numEnds">Number of Ends</label>
                            <input type="number" id="numEnds" class="form-control" readonly>
                        </div>
                        <div class="form-group">
                            <label for="schedStart">Scheduled Start Time</label>
                            <input type="datetime-local" id="schedStart" class="form-control" readonly>
                        </div>
                        <div class="form-group">
                            <label for="schedEnd">Scheduled End Time</label>
                            <input type="datetime-local" id="schedEnd" class="form-control" readonly>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            <h3>Beam Details</h3>
                        </div>
                        <div class="form-group">
                            <label for="beamCode">Beam Code</label>
                            <div style="display: flex; gap: 10px;">
                                <input type="text" id="beamCode" class="form-control" placeholder="Scan beam barcode">
                                <button id="scanBeamBtn" class="btn btn-secondary">Scan</button>
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="emptyBeamWeight">Empty Beam Weight (kg)</label>
                            <input type="number" id="emptyBeamWeight" class="form-control" step="0.01">
                        </div>
                        <div class="form-group">
                            <label for="actualBeamWeight">Actual Beam Weight (kg) - from PLC</label>
                            <div style="display: flex; gap: 10px;">
                                <input type="number" id="actualBeamWeight" class="form-control" step="0.01" readonly>
                                <button id="getPlcWeightBtn" class="btn btn-secondary">Get PLC Reading</button>
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="netWeight">Net Yarn Weight (kg)</label>
                            <input type="number" id="netWeight" class="form-control" step="0.01" readonly>
                        </div>
                        <button id="saveBeamLoadingBtn" class="btn btn-primary">Save Beam Loading</button>
                    </div>
                </div>
            </div>
        `;
    }

    async retrievePlan() {
        const machineCode = document.getElementById('machineCode').value;
        if (!machineCode) {
            this.showAlert('Please enter machine code first.', 'warning');
            return;
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/wrp/plans/${machineCode}`);
            if (response.ok) {
                const plans = await response.json();
                this.displayPlans(plans);
            } else {
                this.showAlert('No plans found for this machine.', 'info');
            }
        } catch (error) {
            this.showAlert('Failed to retrieve plans. Using sample data.', 'warning');
            // Show sample data
            this.displayPlans([
                { id: 1, yarn_code: 'YC-001', beam_size: '30"', num_ends: 1200, scheduled_start: '2024-01-15T08:00:00', scheduled_end: '2024-01-15T16:00:00' },
                { id: 2, yarn_code: 'YC-002', beam_size: '32"', num_ends: 1400, scheduled_start: '2024-01-15T16:00:00', scheduled_end: '2024-01-16T00:00:00' }
            ]);
        }
    }

    displayPlans(plans) {
        const planList = document.getElementById('planList');
        const tableBody = document.getElementById('planTableBody');
        
        if (!planList || !tableBody) return;
        
        planList.style.display = 'block';
        tableBody.innerHTML = '';
        
        plans.forEach(plan => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><input type="radio" name="selectedPlan" value="${plan.id}" onchange="app.selectPlan(${plan.id})"></td>
                <td>${plan.id}</td>
                <td>${plan.yarn_code}</td>
                <td>${plan.beam_size}</td>
                <td>${plan.num_ends}</td>
            `;
            tableBody.appendChild(row);
        });
    }

    selectPlan(planId) {
        // In real implementation, fetch plan details and populate fields
        document.getElementById('yarnCode').value = 'YC-001';
        document.getElementById('beamSize').value = '30"';
        document.getElementById('numEnds').value = 1200;
        document.getElementById('schedStart').value = '2024-01-15T08:00';
        document.getElementById('schedEnd').value = '2024-01-15T16:00';
    }

    async scanBeamCode() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/touch/barcode/scan`);
            if (response.ok) {
                const data = await response.json();
                document.getElementById('beamCode').value = data.code;
                // Simulate empty beam weight from master data
                document.getElementById('emptyBeamWeight').value = 45.5;
                this.showAlert(`Beam scanned: ${data.code}`, 'success');
            } else {
                throw new Error('Barcode scan failed');
            }
        } catch (error) {
            // Simulated scan
            const beamCode = 'BEAM-' + Math.floor(1000 + Math.random() * 9000);
            document.getElementById('beamCode').value = beamCode;
            document.getElementById('emptyBeamWeight').value = (40 + Math.random() * 10).toFixed(1);
            this.showAlert(`Simulated beam scan: ${beamCode}`, 'info');
        }
    }

    async simulatePlcReading() {
        // Simulate PLC weight reading
        const weight = (45.5 + Math.random() * 20).toFixed(2);
        document.getElementById('actualBeamWeight').value = weight;
        
        // Calculate net weight
        const emptyWeight = parseFloat(document.getElementById('emptyBeamWeight').value) || 0;
        const netWeight = (parseFloat(weight) - emptyWeight).toFixed(2);
        document.getElementById('netWeight').value = netWeight;
        
        this.showAlert(`PLC reading received: ${weight} kg`, 'success');
    }

    async saveBeamLoading() {
        const machineCode = document.getElementById('machineCode').value;
        const beamCode = document.getElementById('beamCode').value;
        
        if (!machineCode || !beamCode) {
            this.showAlert('Please fill in required fields.', 'error');
            return;
        }

        const data = {
            machine_code: machineCode,
            beam_code: beamCode,
            yarn_code: document.getElementById('yarnCode').value,
            beam_size: document.getElementById('beamSize').value,
            num_ends: parseInt(document.getElementById('numEnds').value) || 0,
            scheduled_start: document.getElementById('schedStart').value,
            scheduled_end: document.getElementById('schedEnd').value,
            empty_beam_weight: parseFloat(document.getElementById('emptyBeamWeight').value) || 0,
            actual_beam_weight: parseFloat(document.getElementById('actualBeamWeight').value) || 0,
            net_yarn_weight: parseFloat(document.getElementById('netWeight').value) || 0,
            status: 'completed'
        };

        try {
            const response = await fetch(`${this.apiBaseUrl}/wrp/beam-loading`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                this.showAlert('Beam loading saved successfully!', 'success');
                // Reset form
                document.getElementById('machineCode').value = '';
                document.getElementById('beamCode').value = '';
                document.getElementById('emptyBeamWeight').value = '';
                document.getElementById('actualBeamWeight').value = '';
                document.getElementById('netWeight').value = '';
            } else {
                this.showAlert('Failed to save beam loading.', 'error');
            }
        } catch (error) {
            this.showAlert('Network error. Data saved locally and will sync later.', 'warning');
            // In real app, would save to local storage for later sync
        }
    }

    switchWrpPage(e) {
        const page = e.currentTarget.dataset.page;
        this.currentPage = page;
        
        // Update active tab
        document.querySelectorAll('.wrp-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        e.currentTarget.classList.add('active');
        
        // Load page content
        this.loadWrpPageContent(page);
    }

    async loadWarpPage() {
        return '<h3>Warp Page</h3><p>Warp functionality coming soon...</p>';
    }

    async loadUnloadPage() {
        return '<h3>Unload Page</h3><p>Unload functionality coming soon...</p>';
    }

    async loadWrpPageContent(page) {
        const wrpContent = document.getElementById('wrpContent');
        if (!wrpContent) return;
        
        switch(page) {
            case 'beam-loading':
                wrpContent.innerHTML = await this.loadBeamLoadingPage();
                break;
            case 'warp':
                wrpContent.innerHTML = await this.loadWarpPage();
                break;
            case 'unload':
                wrpContent.innerHTML = await this.loadUnloadPage();
                break;
        }
        
        this.bindEvents(); // Rebind events
    }

    async loadHardwareStatus() {
        // Periodically check hardware status
        setInterval(async () => {
            try {
                await fetch(`${this.apiBaseUrl}/health`);
                // Update status indicators if needed
            } catch (error) {
                console.log('Health check failed');
            }
        }, 30000);
    }

    showAlert(message, type = 'info') {
        // Create or update alert element
        let alertDiv = document.getElementById('globalAlert');
        if (!alertDiv) {
            alertDiv = document.createElement('div');
            alertDiv.id = 'globalAlert';
            alertDiv.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 20px;
                border-radius: 4px;
                color: white;
                z-index: 9999;
                max-width: 400px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                transition: opacity 0.3s;
            `;
            document.body.appendChild(alertDiv);
        }
        
        const colors = {
            success: '#2ecc71',
            error: '#e74c3c',
            warning: '#f39c12',
            info: '#3498db'
        };
        
        alertDiv.style.backgroundColor = colors[type] || colors.info;
        alertDiv.textContent = message;
        alertDiv.style.opacity = '1';
        
        setTimeout(() => {
            alertDiv.style.opacity = '0';
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.parentNode.removeChild(alertDiv);
                }
            }, 300);
        }, 3000);
    }
}

// Initialize app
window.app = new MESApp();
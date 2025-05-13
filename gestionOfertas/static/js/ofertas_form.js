// Variables globales
let currentStep = 1;
const totalSteps = 3;
const maxChars = {
  nombre: 100,
  descripcion: 500,
  requisitos: 1000,
  beneficios: 500
};

// Inicialización cuando el DOM está listo
document.addEventListener('DOMContentLoaded', function() {
  initSelect2();
  initCharacterCounters();
  updateProgressBar();
  addInputMasks();
  initAnimations();
  setupStepIndicators();
});

// Inicializar Select2 para selects con animación y estilo mejorado
function initSelect2() {
  $('.form-select').select2({
    theme: 'bootstrap4',
    width: '100%',
    placeholder: 'Selecciona una opción',
    allowClear: true,
    dropdownCssClass: 'select2-dropdown-animated'
  }).on('select2:open', function() {
    document.querySelector('.select2-search__field').focus();
  });
}

// Configurar contadores de caracteres con retroalimentación visual
function initCharacterCounters() {
  // Configurar para cada campo con maxlength
  Object.keys(maxChars).forEach(field => {
    const input = document.getElementById(`id_${field}`);
    if (input) {
      input.setAttribute('maxlength', maxChars[field]);
      input.addEventListener('input', updateCharacterCounter);
      // Actualizar contador al cargar (por si hay valores predefinidos)
      updateCharacterCounter.call(input);
    }
  });
}

// Actualizar contador de caracteres con efectos visuales
function updateCharacterCounter() {
  const fieldName = this.id.replace('id_', '');
  const counter = document.getElementById(`${fieldName}-counter`);
  if (!counter) return;
  
  const charCount = this.value.length;
  const maxLength = maxChars[fieldName];
  const percentage = (charCount / maxLength) * 100;
  
  counter.textContent = charCount;
  counter.parentElement.className = 'char-counter';
  
  if (percentage > 80 && percentage < 90) {
    counter.parentElement.classList.add('warning');
  } else if (percentage >= 90) {
    counter.parentElement.classList.add('danger');
  }
  
  // Efecto de pulso al acercarse al límite
  if (percentage > 95) {
    counter.parentElement.classList.add('pulse');
    setTimeout(() => {
      counter.parentElement.classList.remove('pulse');
    }, 500);
  }
}

// Agregar máscaras para campos específicos
function addInputMasks() {
  // Máscara para salario (formato de moneda)
  const salarioInput = document.getElementById('id_salario');
  if (salarioInput) {
    salarioInput.addEventListener('input', function(e) {
      // Eliminar caracteres no numéricos
      this.value = this.value.replace(/[^0-9]/g, '');
      
      // Efecto visual de confirmación
      if (this.value) {
        this.classList.add('has-value');
      } else {
        this.classList.remove('has-value');
      }
    });
  }
  
  // Animación para campos de fecha
  const dateInput = document.getElementById('id_fecha_cierre');
  if (dateInput) {
    dateInput.addEventListener('change', function() {
      if (this.value) {
        this.classList.add('date-selected');
      } else {
        this.classList.remove('date-selected');
      }
    });
  }
}

// Inicializar animaciones para elementos del formulario
function initAnimations() {
  // Efecto de aparición para etiquetas de formulario
  document.querySelectorAll('.form-label').forEach((label, index) => {
    label.style.opacity = '0';
    label.style.transform = 'translateY(10px)';
    
    setTimeout(() => {
      label.style.transition = 'all 0.3s ease';
      label.style.opacity = '1';
      label.style.transform = 'translateY(0)';
    }, 100 + (index * 50));
  });
  
  // Animación para la tarjeta
  const formCard = document.querySelector('.form-card');
  if (formCard) {
    formCard.style.opacity = '0';
    formCard.style.transform = 'translateY(20px)';
    
    setTimeout(() => {
      formCard.style.transition = 'all 0.6s ease';
      formCard.style.opacity = '1';
      formCard.style.transform = 'translateY(0)';
    }, 300);
  }
}

// Configurar indicadores de pasos interactivos
function setupStepIndicators() {
  document.querySelectorAll('.step-label').forEach(indicator => {
    indicator.addEventListener('click', function() {
      const targetStep = parseInt(this.getAttribute('data-step'));
      if (targetStep < currentStep) {
        showStep(targetStep);
      } else if (validateStepsBeforeJump(targetStep)) {
        showStep(targetStep);
      }
    });
  });
}

// Validar pasos previos antes de saltar a uno posterior
function validateStepsBeforeJump(targetStep) {
  for (let i = 1; i < targetStep; i++) {
    if (!validateStep(i, false)) {
      // Mostrar el primer paso con errores
      showStep(i);
      showToast('Por favor completa correctamente el paso ' + i + ' antes de continuar', 'warning');
      return false;
    }
  }
  return true;
}

// Actualizar barra de progreso y marcadores de paso con animación
function updateProgressBar() {
  const progressPercentage = (currentStep / totalSteps) * 100;
  const progressBar = document.querySelector('.progress-bar');
  
  // Animación suave
  progressBar.style.transition = 'width 0.6s ease';
  progressBar.style.width = `${progressPercentage}%`;
  
  // Actualizar indicadores de paso
  document.querySelectorAll('.step-label').forEach((label, index) => {
    label.classList.remove('active-step', 'completed');
    
    if (index + 1 < currentStep) {
      label.classList.add('completed');
      label.innerHTML = '<i class="fas fa-check"></i>';
    } else if (index + 1 === currentStep) {
      label.classList.add('active-step');
      label.textContent = index + 1;
    } else {
      label.textContent = index + 1;
    }
  });
}

// Mostrar paso específico con animaciones
function showStep(step) {
  const currentStepElement = document.getElementById(`step-${currentStep}`);
  const nextStepElement = document.getElementById(`step-${step}`);
  
  if (step > currentStep) {
    // Animación hacia adelante
    currentStepElement.style.animation = 'slideOut 0.3s forwards';
    
    setTimeout(() => {
      currentStepElement.classList.remove('active');
      nextStepElement.classList.add('active');
      nextStepElement.style.animation = 'slideIn 0.3s forwards';
    }, 300);
  } else {
    // Animación hacia atrás
    currentStepElement.style.animation = 'slideIn 0.3s reverse forwards';
    
    setTimeout(() => {
      currentStepElement.classList.remove('active');
      nextStepElement.classList.add('active');
      nextStepElement.style.animation = 'slideOut 0.3s reverse forwards';
    }, 300);
  }
  
  currentStep = step;
  updateProgressBar();
  
  // Desplazar al principio del paso con animación suave
  setTimeout(() => {
    nextStepElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, 350);
}

// Validar paso actual con retroalimentación mejorada
function validateStep(step, showFeedback = true) {
  let isValid = true;
  const stepDiv = document.getElementById(`step-${step}`);
  
  // Resetear validaciones previas
  stepDiv.querySelectorAll('.is-invalid').forEach(el => {
    el.classList.remove('is-invalid');
  });
  
  stepDiv.querySelectorAll('.invalid-feedback').forEach(el => {
    el.style.display = 'none';
  });

  // Validar campos requeridos con efectos
  const requiredInputs = stepDiv.querySelectorAll('[required]');
  requiredInputs.forEach(input => {
    if (!input.value.trim()) {
      input.classList.add('is-invalid');
      
      // Efecto de shake para campos inválidos
      if (showFeedback) {
        input.style.animation = 'shake 0.5s';
        setTimeout(() => {
          input.style.animation = '';
        }, 500);
      }
      
      const feedback = input.nextElementSibling;
      let feedbackEl = feedback;
      
      while (feedbackEl && !feedbackEl.classList.contains('invalid-feedback')) {
        feedbackEl = feedbackEl.nextElementSibling;
      }
      
      if (feedbackEl && feedbackEl.classList.contains('invalid-feedback')) {
        feedbackEl.style.display = 'block';
      }
      
      isValid = false;
    }
  });

  // Validación adicional para fecha
  const dateInput = stepDiv.querySelector('input[type="date"]');
  if (dateInput && dateInput.value) {
    const selectedDate = new Date(dateInput.value);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    if (selectedDate < today) {
      dateInput.classList.add('is-invalid');
      
      if (showFeedback) {
        dateInput.style.animation = 'shake 0.5s';
        setTimeout(() => {
          dateInput.style.animation = '';
        }, 500);
      }
      
      let feedbackEl = dateInput.nextElementSibling;
      while (feedbackEl && !feedbackEl.classList.contains('invalid-feedback')) {
        feedbackEl = feedbackEl.nextElementSibling;
      }
      
      if (feedbackEl && feedbackEl.classList.contains('invalid-feedback')) {
        feedbackEl.textContent = 'La fecha no puede ser anterior a hoy';
        feedbackEl.style.display = 'block';
      }
      
      isValid = false;
    }
  }

  // Si hay errores y debemos mostrar feedback, desplazar al primero
  if (!isValid && showFeedback) {
    const firstInvalid = stepDiv.querySelector('.is-invalid');
    if (firstInvalid) {
      firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
      firstInvalid.focus();
    }
  }

  return isValid;
}

// Navegación entre pasos con validación
function nextStep() {
  if (validateStep(currentStep)) {
    if (currentStep < totalSteps) {
      showStep(currentStep + 1);
      showToast('¡Paso completado correctamente!', 'success');
    }
  } else {
    showToast('Por favor completa todos los campos requeridos', 'error');
  }
}

function prevStep() {
  if (currentStep > 1) {
    showStep(currentStep - 1);
  }
}

// Toast personalizado para notificaciones
// Toast personalizado para notificaciones
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    let icon = 'info-circle';
    let bgColor = 'var(--primary-color)';
    
    // Configurar apariencia según tipo
    switch(type) {
      case 'success':
        icon = 'check-circle';
        bgColor = 'var(--secondary-color)';
        break;
      case 'warning':
        icon = 'exclamation-triangle';
        bgColor = 'var(--accent-color)';
        break;
      case 'error':
        icon = 'times-circle';
        bgColor = 'var(--danger-color)';
        break;
    }
    
    // Crear elemento toast
    toast.className = 'custom-toast animate__animated animate__fadeInUp';
    toast.style.position = 'fixed';
    toast.style.bottom = '20px';
    toast.style.right = '20px';
    toast.style.backgroundColor = bgColor;
    toast.style.color = 'white';
    toast.style.padding = '12px 20px';
    toast.style.borderRadius = '8px';
    toast.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
    toast.style.zIndex = '9999';
    toast.style.minWidth = '250px';
    toast.style.display = 'flex';
    toast.style.alignItems = 'center';
    
    toast.innerHTML = `
      <i class="fas fa-${icon} me-2"></i>
      <span>${message}</span>
    `;
    
    document.body.appendChild(toast);
    
    // Animar salida y eliminar
    setTimeout(() => {
      toast.style.animation = 'fadeOutDown 0.5s forwards';
      setTimeout(() => {
        toast.remove();
      }, 500);
    }, 3000);
  }
  
  // Validar formulario antes de enviar con resumen
  document.getElementById('ofertaForm').addEventListener('submit', function(e) {
    let isValid = true;
    
    // Validar todos los pasos
    for (let step = 1; step <= totalSteps; step++) {
      if (!validateStep(step, step === currentStep)) {
        isValid = false;
        // Mostrar el paso con errores solo si no es el paso actual
        if (currentStep !== step) {
          showStep(step);
        }
        break;
      }
    }
    
    if (!isValid) {
      e.preventDefault();
      // Mostrar alerta mejorada si hay errores
      showToast('Por favor completa todos los campos requeridos correctamente', 'error');
    } else {
      // Mostrar animación de envío
      const submitBtn = e.submitter;
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Enviando...';
        
        // Animación de éxito antes de enviar
        showToast('¡Formulario validado correctamente! Enviando...', 'success');
        
        // Esta línea hace que se siga enviando después de la animación
        // Si se desea enviar inmediatamente, se puede quitar este setTimeout
        setTimeout(() => {
          return true;
        }, 1000);
      }
    }
  });
  
  // Mejoras interactivas para campos del formulario
  document.addEventListener('DOMContentLoaded', function() {
    // Efectos para inputs al recibir y perder foco
    document.querySelectorAll('.form-control, .form-select').forEach(input => {
      // Labels flotantes
      input.addEventListener('focus', function() {
        const label = this.previousElementSibling;
        if (label && label.classList.contains('form-label')) {
          label.classList.add('focused');
        }
        this.parentElement.classList.add('input-focused');
      });
      
      input.addEventListener('blur', function() {
        const label = this.previousElementSibling;
        if (label && label.classList.contains('form-label')) {
          if (!this.value) {
            label.classList.remove('focused');
          }
        }
        this.parentElement.classList.remove('input-focused');
      });
      
      // Pre-llenar con valores existentes
      if (input.value) {
        const label = input.previousElementSibling;
        if (label && label.classList.contains('form-label')) {
          label.classList.add('focused');
        }
      }
    });
    
    // Efecto de ripple para botones
    document.querySelectorAll('.btn').forEach(button => {
      button.addEventListener('click', function(e) {
        const ripple = document.createElement('span');
        ripple.classList.add('ripple');
        
        const diameter = Math.max(this.clientWidth, this.clientHeight);
        const radius = diameter / 2;
        
        ripple.style.width = ripple.style.height = `${diameter}px`;
        ripple.style.left = `${e.clientX - this.getBoundingClientRect().left - radius}px`;
        ripple.style.top = `${e.clientY - this.getBoundingClientRect().top - radius}px`;
        
        this.appendChild(ripple);
        
        setTimeout(() => {
          ripple.remove();
        }, 600);
      });
    });
    
    // Mostrar resumen dinámico en el último paso
    if (document.getElementById('step-3')) {
      const summaryContainer = document.createElement('div');
      summaryContainer.className = 'summary-container mb-4 p-3 border rounded';
      summaryContainer.style.display = 'none';
      summaryContainer.innerHTML = '<h6 class="summary-title mb-3"><i class="fas fa-check-circle me-2"></i>Resumen de tu oferta</h6><div id="summary-content"></div>';
      
      document.getElementById('step-3').insertBefore(summaryContainer, document.getElementById('step-3').firstChild.nextSibling);
      
      // Actualizar resumen cuando se llega al paso 3
      document.addEventListener('showStep', function(e) {
        if (e.detail.step === 3) {
          updateSummary();
        }
      });
    }
  });
  
  // Evento personalizado para cambio de paso
  function showStep(step) {
    const currentStepElement = document.getElementById(`step-${currentStep}`);
    const nextStepElement = document.getElementById(`step-${step}`);
    
    if (step > currentStep) {
      // Animación hacia adelante
      currentStepElement.style.animation = 'slideOut 0.3s forwards';
      
      setTimeout(() => {
        currentStepElement.classList.remove('active');
        nextStepElement.classList.add('active');
        nextStepElement.style.animation = 'slideIn 0.3s forwards';
      }, 300);
    } else {
      // Animación hacia atrás
      currentStepElement.style.animation = 'slideIn 0.3s reverse forwards';
      
      setTimeout(() => {
        currentStepElement.classList.remove('active');
        nextStepElement.classList.add('active');
        nextStepElement.style.animation = 'slideOut 0.3s reverse forwards';
      }, 300);
    }
    
    currentStep = step;
    updateProgressBar();
    
    // Desplazar al principio del paso con animación suave
    setTimeout(() => {
      nextStepElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 350);
    
    // Disparar evento para otros componentes
    document.dispatchEvent(new CustomEvent('showStep', {
      detail: { step: step }
    }));
  }
  
  // Actualizar resumen dinámico
  function updateSummary() {
    const summaryContainer = document.querySelector('.summary-container');
    const summaryContent = document.getElementById('summary-content');
    
    if (!summaryContainer || !summaryContent) return;
    
    // Recoger datos del formulario
    const formData = {
      nombre: document.getElementById('id_nombre')?.value || '',
      categoria: document.getElementById('id_categoria')?.options[document.getElementById('id_categoria')?.selectedIndex]?.text || '',
      descripcion: document.getElementById('id_descripcion')?.value || '',
      requisitos: document.getElementById('id_requisitos')?.value || '',
      beneficios: document.getElementById('id_beneficios')?.value || '',
      salario: document.getElementById('id_salario')?.value || '',
      fecha_cierre: document.getElementById('id_fecha_cierre')?.value || ''
    };
    
    // Formato de fecha más amigable
    let fechaFormateada = '';
    if (formData.fecha_cierre) {
      const fecha = new Date(formData.fecha_cierre);
      fechaFormateada = fecha.toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' });
    }
    
    // Construir HTML del resumen
    summaryContent.innerHTML = `
      <div class="summary-item">
        <strong><i class="fas fa-tag me-2"></i>Título:</strong> ${formData.nombre}
      </div>
      <div class="summary-item">
        <strong><i class="fas fa-folder me-2"></i>Categoría:</strong> ${formData.categoria}
      </div>
      <div class="summary-item">
        <strong><i class="fas fa-align-left me-2"></i>Descripción:</strong> ${formData.descripcion.length > 100 ? formData.descripcion.substring(0, 100) + '...' : formData.descripcion}
      </div>
      ${formData.salario ? `
      <div class="summary-item">
        <strong><i class="fas fa-dollar-sign me-2"></i>Salario:</strong> $${formData.salario}
      </div>` : ''}
      ${fechaFormateada ? `
      <div class="summary-item">
        <strong><i class="fas fa-calendar-alt me-2"></i>Fecha de cierre:</strong> ${fechaFormateada}
      </div>` : ''}
    `;
    
    // Mostrar con animación
    summaryContainer.style.display = 'block';
    summaryContainer.style.opacity = '0';
    summaryContainer.style.transform = 'translateY(10px)';
    
    setTimeout(() => {
      summaryContainer.style.transition = 'all 0.5s ease';
      summaryContainer.style.opacity = '1';
      summaryContainer.style.transform = 'translateY(0)';
    }, 100);
  }
  
  // Agregar animaciones CSS
  document.addEventListener('DOMContentLoaded', function() {
    const style = document.createElement('style');
    style.textContent = `
      @keyframes shake {
        0%, 100% { transform: translateX(0); }
        10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
        20%, 40%, 60%, 80% { transform: translateX(5px); }
      }
      
      @keyframes fadeOutDown {
        from { opacity: 1; transform: translateY(0); }
        to { opacity: 0; transform: translateY(20px); }
      }
      
      @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
      }
      
      .pulse {
        animation: pulse 0.5s infinite;
      }
      
      .form-label.focused {
        color: var(--primary-color);
        transform: translateY(-5px) scale(0.95);
        transform-origin: left;
        transition: all 0.3s ease;
      }
      
      .input-focused {
        position: relative;
      }
      
      .input-focused::after {
        content: '';
        position: absolute;
        bottom: -2px;
        left: 0;
        width: 100%;
        height: 2px;
        background: var(--primary-color);
        animation: inputFocus 0.3s forwards;
      }
      
      @keyframes inputFocus {
        from { transform: scaleX(0); }
        to { transform: scaleX(1); }
      }
      
      .ripple {
        position: absolute;
        border-radius: 50%;
        background-color: rgba(255, 255, 255, 0.3);
        transform: scale(0);
        animation: ripple 0.6s linear;
        pointer-events: none;
      }
      
      @keyframes ripple {
        to { transform: scale(4); opacity: 0; }
      }
      
      .summary-container {
        background-color: #f9f9f9;
        border-radius: 8px;
      }
      
      .summary-title {
        color: var(--primary-color);
        border-bottom: 1px solid #eee;
        padding-bottom: 10px;
      }
      
      .summary-item {
        padding: 8px 0;
        border-bottom: 1px dashed #eee;
      }
      
      .summary-item:last-child {
        border-bottom: none;
      }
      
      .date-selected {
        border-color: var(--primary-color) !important;
        background-color: rgba(52, 152, 219, 0.05) !important;
      }
      
      .has-value {
        font-weight: 500;
        color: var(--dark-color);
      }
      
      /* Animaciones para Select2 */
      .select2-dropdown-animated {
        animation: select2In 0.3s ease;
      }
      
      @keyframes select2In {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
      }
    `;
    
    document.head.appendChild(style);
  });
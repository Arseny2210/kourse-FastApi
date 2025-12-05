// static/js/dashboard.js
document.addEventListener('DOMContentLoaded', function () {
	// Обработчик для формы добавления карточки
	const flashcardForm = document.getElementById('add-flashcard-form')
	if (flashcardForm) {
		flashcardForm.addEventListener('submit', function (e) {
			const foreignWord = document.getElementById('foreign_word').value.trim()
			const nativeWord = document.getElementById('native_word').value.trim()

			if (!foreignWord || !nativeWord) {
				e.preventDefault()
				alert('Иностранное слово и перевод обязательны!')
				return
			}

			if (foreignWord.length > 100 || nativeWord.length > 100) {
				e.preventDefault()
				alert('Слова не должны превышать 100 символов!')
				return
			}

			const example = document.getElementById('example').value
			if (example && example.length > 500) {
				e.preventDefault()
				alert('Пример не должен превышать 500 символов!')
				return
			}

			// Показываем сообщение о загрузке
			const submitBtn = this.querySelector('button[type="submit"]')
			const originalText = submitBtn.textContent
			submitBtn.textContent = 'Добавление...'
			submitBtn.disabled = true
		})
	}

	// Автоматическая подсветка карточек
	const flashcards = document.querySelectorAll('.flashcard')
	flashcards.forEach(card => {
		card.addEventListener('click', function () {
			this.classList.toggle('flipped')
		})
	})
})

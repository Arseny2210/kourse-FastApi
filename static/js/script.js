document.addEventListener('DOMContentLoaded', function () {
	const loginForm = document.getElementById('login-form')
	if (loginForm) {
		loginForm.addEventListener('submit', async function (e) {
			e.preventDefault()

			const username = document.getElementById('username').value
			const password = document.getElementById('password').value
			const errorElement = document.getElementById('login-error')

			errorElement.textContent = ''

			try {
				const response = await fetch('/web/login', {
					method: 'POST',
					headers: {
						'Content-Type': 'application/x-www-form-urlencoded',
					},
					body: new URLSearchParams({
						username: username,
						password: password,
					}),
				})

				const text = await response.text()

				if (response.ok) {
					window.location.href = '/dashboard'
				} else {
					try {
						const data = JSON.parse(text)
						errorElement.textContent = data.detail || 'Ошибка входа'
					} catch {
						document.body.innerHTML = text
					}
				}
			} catch (error) {
				errorElement.textContent = 'Ошибка подключения к серверу'
				console.error('Login error:', error)
			}
		})
	}

	const registerForm = document.getElementById('register-form')
	if (registerForm) {
		registerForm.addEventListener('submit', async function (e) {
			e.preventDefault()

			const username = document.getElementById('reg-username').value
			const password = document.getElementById('reg-password').value
			const errorElement = document.getElementById('register-error')
			const successElement = document.getElementById('register-success')

			errorElement.textContent = ''
			successElement.textContent = ''

			try {
				const response = await fetch('/web/register', {
					method: 'POST',
					headers: {
						'Content-Type': 'application/x-www-form-urlencoded',
					},
					body: new URLSearchParams({
						username: username,
						password: password,
					}),
				})

				const text = await response.text()

				if (response.ok) {
					successElement.textContent =
						'Регистрация успешна! Теперь вы можете войти.'
					document.getElementById('reg-username').value = ''
					document.getElementById('reg-password').value = ''
				} else {
					try {
						const data = JSON.parse(text)
						errorElement.textContent = data.detail || 'Ошибка регистрации'
					} catch {
						document.body.innerHTML = text
					}
				}
			} catch (error) {
				errorElement.textContent = 'Ошибка подключения к серверу'
				console.error('Register error:', error)
			}
		})
	}
})

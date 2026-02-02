import requests
from requests.exceptions import RequestException, Timeout, ConnectionError
from app.core.config import settings


class SMSServiceError(Exception):
    """Исключение для ошибок SMS сервиса"""
    pass


class SMSService:
    """Сервис для отправки SMS через API (точно как в примере)"""
    
    base_url = settings.SMS_API_URL
    timeout = 30  # Таймаут для запросов в секундах

    def __get_token(self):
        """Получение токена авторизации для SMS API (точно как в примере)"""
        try:
            if not self.base_url:
                raise SMSServiceError("SMS_API_URL не настроен в переменных окружения")
            
            if not settings.SMS_AUTH_EMAIL or not settings.SMS_AUTH_SECRET_KEY:
                raise SMSServiceError("SMS_AUTH_EMAIL и SMS_AUTH_SECRET_KEY должны быть настроены")
            
            response = requests.post(
                url=f"{self.base_url}/auth/login/",
                data={
                    "email": settings.SMS_AUTH_EMAIL,
                    "password": settings.SMS_AUTH_SECRET_KEY,
                },
                timeout=self.timeout
            )
            
            # Проверяем HTTP статус
            response.raise_for_status()
            
            res = response.json()
            
            # Проверяем структуру ответа
            if "data" not in res or "token" not in res["data"]:
                print(f"[SMS] Unexpected response structure: {res}")
                raise SMSServiceError("Неверная структура ответа от SMS API при получении токена")
            
            return res["data"]["token"]
            
        except Timeout:
            raise SMSServiceError("Таймаут при получении токена от SMS API")
        except ConnectionError:
            raise SMSServiceError("Ошибка подключения к SMS API")
        except requests.exceptions.HTTPError as e:
            print(f"[SMS] HTTP error getting token: {e.response.status_code} - {e.response.text}")
            raise SMSServiceError(f"Ошибка HTTP при получении токена: {e.response.status_code}")
        except Exception as e:
            print(f"[SMS] Error getting token: {str(e)}")
            raise SMSServiceError(f"Ошибка при получении токена: {str(e)}")

    def send_message(self, phone_number, message):
        """Отправка SMS сообщения (точно как в примере)"""
        # Если это тестовый номер, пропускаем отправку
        if phone_number == settings.SMS_MAIN_PHONE_NUMBER:
            print(f"[SMS] Test phone number {phone_number}, skipping SMS send")
            return
            
        try:
            if not self.base_url:
                print("[SMS] ERROR: SMS_API_URL не настроен")
                raise SMSServiceError("SMS_API_URL не настроен в переменных окружения")
            
            token = self.__get_token()
            payload = {
                "mobile_phone": phone_number, 
                "message": message, 
                "from": settings.SMS_FROM_NUMBER
            }
            headers = {"Authorization": f"Bearer {token}"}
            
            print(f"[SMS] Sending message to {phone_number} via {self.base_url}/message/sms/send")
            
            response = requests.post(
                url=f"{self.base_url}/message/sms/send",
                headers=headers,
                data=payload,
                timeout=self.timeout
            )
            
            # Проверяем HTTP статус
            response.raise_for_status()
            
            result = response.json()
            print(f"[SMS] Response: {result}")
            
            # Проверяем статус в ответе
            if isinstance(result, dict):
                status = result.get("status", "").lower()
                message_text = result.get("message", "")
                
                # Статус "waiting" означает, что сообщение поставлено в очередь
                # Это нормальное состояние для асинхронных SMS провайдеров
                if status == "waiting":
                    print(f"[SMS] Message queued successfully. ID: {result.get('id', 'N/A')}")
                    return result
                elif status in ["sent", "delivered", "success", "ok"]:
                    print(f"[SMS] Message sent successfully. ID: {result.get('id', 'N/A')}")
                    return result
                elif status in ["error", "failed", "rejected"]:
                    error_msg = message_text or "Неизвестная ошибка при отправке SMS"
                    print(f"[SMS] ERROR: {error_msg}")
                    raise SMSServiceError(f"Ошибка отправки SMS: {error_msg}")
                else:
                    # Если статус не определен, считаем успешным если HTTP статус 200
                    print(f"[SMS] Unknown status '{status}', but HTTP 200. Assuming success.")
                    return result
            
            return result
            
        except Timeout:
            print("[SMS] ERROR: Таймаут при отправке SMS")
            raise SMSServiceError("Таймаут при отправке SMS")
        except ConnectionError:
            print("[SMS] ERROR: Ошибка подключения к SMS API")
            raise SMSServiceError("Ошибка подключения к SMS API")
        except requests.exceptions.HTTPError as e:
            error_text = e.response.text if hasattr(e, 'response') else str(e)
            print(f"[SMS] HTTP error: {e.response.status_code} - {error_text}")
            raise SMSServiceError(f"Ошибка HTTP при отправке SMS: {e.response.status_code}")
        except SMSServiceError:
            raise
        except Exception as e:
            print(f"[SMS] Unexpected error: {str(e)}")
            raise SMSServiceError(f"Неожиданная ошибка при отправке SMS: {str(e)}")

    def get_templates(self):
        """Получение шаблонов SMS (как в примере)"""
        try:
            token = self.__get_token()
            response = requests.get(
                f"{self.base_url}/users/templates",
                headers={"Authorization": f"Bearer {token}"},
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            print(f"[SMS] Templates: {result}")
            return result
        except Exception as e:
            print(f"[SMS] Error getting templates: {str(e)}")
            raise SMSServiceError(f"Ошибка при получении шаблонов: {str(e)}")

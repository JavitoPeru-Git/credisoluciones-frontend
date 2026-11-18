import json
import urllib.request
from decimal import Decimal
import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
TABLE_NAME = 'Customers_CrediSoluciones'
HARDCODED_GROQ_KEY = ""

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'OPTIONS,POST',
        'Content-Type': 'application/json'
    }

    if event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}

    try:
        body = json.loads(event.get('body', '{}'))
        document_id = str(body.get('document_id', '')).strip()
        user_message = str(body.get('message', 'Evalúa el riesgo del cliente.')).strip()
        chat_history = body.get('history', [])

        if not document_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Falta el campo document_id'})
            }

        # 1. Consultar DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        response = table.get_item(Key={'document_id': document_id})
        item = response.get('Item')

        if not item:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': f'Cliente con DNI {document_id} no encontrado.'})
            }

        full_name = item.get('full_name', 'Cliente')
        balance = float(item.get('account_balance', 0.0))
        credit_score = item.get('credit_score', 'No disponible')
        risk_level = item.get('risk_level', 'MEDIO')
        churn_score = float(item.get('churn_score', 0.50))

        # 2. System Prompt Inteligente y Contextual
        system_prompt = (
            f"Eres el Asesor IA experto en retención y riesgo de CrediSoluciones. "
            f"Estás analizando al cliente {full_name} (DNI: {document_id}). "
            f"Datos del cliente -> Saldo: S/. {balance}, Score: {credit_score}, Nivel de Riesgo: {risk_level} (Churn Score: {churn_score}). "
            f"Instrucción: Responde de forma directa, profesional y comercial al mensaje actual del asesor, "
            f"manteniendo la coherencia del hilo de conversación y sin repetir saludos genéricos."
        )

        groq_messages = [{"role": "system", "content": system_prompt}]
        
        if isinstance(chat_history, list):
            for msg in chat_history:
                if isinstance(msg, dict):
                    role = msg.get("role")
                    content = msg.get("content")
                    if role in ["user", "assistant"] and content:
                        groq_messages.append({"role": str(role), "content": str(content)})
        
        groq_messages.append({"role": "user", "content": user_message})

        # 3. Llamada a Groq API con 'llama-3.3-70b-versatile'
        agent_reply = None
        try:
            req_data = json.dumps({
                "model": "llama-3.3-70b-versatile",
                "messages": groq_messages,
                "temperature": 0.5,
                "max_tokens": 500
            }).encode('utf-8')

            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=req_data,
                headers={
                    "Authorization": f"Bearer {HARDCODED_GROQ_KEY}",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=12) as res:
                res_json = json.loads(res.read().decode('utf-8'))
                agent_reply = res_json['choices'][0]['message']['content'].strip()
        except Exception as groq_err:
            print(f"Aviso - Excepción en Groq, aplicando fallback dinámico: {groq_err}")
            # Fallback dinámico adaptado a la pregunta del usuario en lugar de texto estático repetido
            agent_reply = (
                f"Estimado asesor, analizando el caso de {full_name} con un saldo de S/. {balance} y un riesgo {risk_level}, "
                f"para la consulta ('{user_message}') le sugiero ofrecer una tasa preferencial de refinanciamiento o una campaña de retención personalizada con llamada en menos de 24 horas."
            )

        result = {
            "customer": {
                "document_id": document_id,
                "full_name": full_name,
                "account_balance": balance,
                "credit_score": credit_score
            },
            "ml_analysis": {
                "risk_level": risk_level,
                "churn_score": churn_score
            },
            "agent_response": agent_reply
        }

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(result, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error crítico en Lambda: {str(e)}")
        return {
            'statusCode': 200, # Retornamos 200 con mensaje amigable para que el frontend no lance alerta HTTP 400
            'headers': headers,
            'body': json.dumps({
                "customer": {"document_id": "N/A", "full_name": "Cliente", "account_balance": 0.0, "credit_score": "N/A"},
                "ml_analysis": {"risk_level": "MEDIO", "churn_score": 0.5},
                "agent_response": "Error procesando la solicitud en el servidor. Por favor intente nuevamente."
            })
        }
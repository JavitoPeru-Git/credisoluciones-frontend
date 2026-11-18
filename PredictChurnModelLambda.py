import json

def lambda_handler(event, context):
    try:
        # Intentamos obtener el cuerpo de la petición (body) si viene desde un API Gateway
        body = {}
        if 'body' in event:
            body = json.loads(event['body'])
        else:
            body = event # Permite probarlo directamente desde la consola de AWS
            
        # Extraemos el saldo de la cuenta (si no viene, por defecto asumimos 1500)
        balance = float(body.get('account_balance', 1500.0))
        
        # Lógica simulada del modelo de Machine Learning (Churn/Abandono)
        # Si el saldo es menor a 2000, el modelo predice un riesgo de abandono alto
        if balance < 2000.0:
            risk_score = 0.82
            risk_level = "ALTO"
            recommendation = "Ofrecer tasa preferencial de retención y bono de permanencia."
        else:
            risk_score = 0.18
            risk_level = "BAJO"
            recommendation = "Cliente estable. Mantener comunicación estándar."
            
        # Retornamos la respuesta estructurada de la API de ML
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'model_name': 'ChurnPredictionModel_v1',
                'churn_risk_score': risk_score,
                'risk_level': risk_level,
                'recommendation': recommendation
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

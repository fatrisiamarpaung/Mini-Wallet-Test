from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime
import uuid

app = Flask(__name__)

app.config['JWT_SECRET_KEY'] = 'super-secret-key'
jwt = JWTManager(app)
wallets = {}  

# Create Account Wallet
@app.route('/api/v1/init', methods=['POST'])
def init_acc():
    data = request.get_json()
    cust_id = data.get('cust_id')

    if cust_id is None or not cust_id.strip():
        error_response = {
            "data": {
                "error": {
                    "customer_xid": [
                        "Missing data for required field"
                    ]
                }
            },
            "status": "fail"
        }
        return jsonify(error_response), 400

    if cust_id in wallets:
        return jsonify({"status" : "error", "message": "Customer ID already exists."}), 400

    access_token = create_access_token(identity=cust_id) 
    wallets[cust_id] = {
        'cust_id': cust_id, 
        'balance': 0, 
        'token': access_token, 
        'wallet_enabled': False,
        'transactions': []
    }  

    response_data = {"data": {"token": access_token}, "status": "success"}
    return jsonify(response_data)

# Enable Wallet
@app.route('/api/v1/wallet', methods=['POST'])
@jwt_required()
def enable_wallet():
    current_cust_id = get_jwt_identity()
    if current_cust_id in wallets:
        if not wallets[current_cust_id]['wallet_enabled']:
            wallet_id = str(uuid.uuid4())
            wallets[current_cust_id]['wallet_id'] = wallet_id
            wallets[current_cust_id]['wallet_enabled'] = True
            wallets[current_cust_id]['enabled_at'] = datetime.now().isoformat()

            response_data = {
                "status": "success",
                "data": {
                    "wallet": {
                        "id": wallet_id,
                        "owned_by": current_cust_id,
                        "status": "enabled",
                        "enabled_at": wallets[current_cust_id]['enabled_at'],
                        "balance": wallets[current_cust_id]['balance']
                    }
                }
            }
            return jsonify(response_data)
        else:
            return jsonify({"status": "fail", "data":{"error": "Wallet is already enabled"}}, 400)
    else:
        return jsonify({"status": "error", "message": "Customer ID not found."}, 404)

# Get View Wallet Balance 
@app.route('/api/v1/wallet', methods=['GET'])
@jwt_required()
def view_balance():
    current_cust_id = get_jwt_identity()
    if current_cust_id in wallets:
        if wallets[current_cust_id].get('is_disabled', False):
            return jsonify({"status": "fail", "data": {"error": "Wallet is disabled"}}, 400)
        if wallets[current_cust_id]['wallet_enabled']:
            wallet_data = {
                "id": wallets[current_cust_id]['wallet_id'],
                "owned_by": current_cust_id,
                "status": "enabled",
                "enabled_at": wallets[current_cust_id]['enabled_at'],
                "balance": wallets[current_cust_id]['balance']
            }
            response_data = {
                "status": "success",
                "data": {
                    "wallet": wallet_data
                }
            }
            return jsonify(response_data)
        else:
            return jsonify({"status": "fail", "data":{"error": "Wallet disabled."}}), 400
    else:
        return jsonify({"status": "error", "message": "Customer ID not found."}), 404

# Add Virtual Money
@app.route('/api/v1/wallet/deposits', methods=['POST'])
@jwt_required()
def add_virtual_money():
    current_cust_id = get_jwt_identity()
    if current_cust_id in wallets:
        if wallets[current_cust_id].get('is_disabled', False):
            return jsonify({"status": "fail", "data": {"error": "Wallet is disabled"}}, 400)
        data = request.get_json()
        reference_id = data.get('reference_id')
        amount = data.get('amount')

        if reference_id is None or not reference_id.strip():
            error_response = {
                "data": {
                    "error": {
                        "reference_id": [
                            "Missing data for required field"
                        ]
                    }
                },
                "status": "fail"
            }
            return jsonify(error_response), 400
        
        if amount is None or amount < 0:
            error_response = {
                "data": {
                    "error": {
                        "amount": [
                            "Amount must be greater than 0."
                        ]
                    }
                },
                "status": "fail"
            }
            return jsonify(error_response), 400
        
        if wallets[current_cust_id]['wallet_enabled']:
            deposit_id = str(uuid.uuid4())
            deposited_at = datetime.now().isoformat()

            # Add the transaction to the customer's record
            transaction = {
                "id": deposit_id,
                "type": "deposit",
                "amount": amount,
                "status": "success",
                "transacted_at": deposited_at,
                "reference_id": reference_id
            }

            wallets[current_cust_id]['transactions'].append(transaction)
            wallets[current_cust_id]['balance'] += amount

            response_data = {
                "status": "success",
                "data": {
                    "deposit": {
                        "id": deposit_id,
                        "deposited_by": current_cust_id,
                        "status": "success",
                        "deposited_at": deposited_at,
                        "amount": amount,
                        "reference_id": reference_id
                    }
                }
            }
            return jsonify(response_data)
        else:
            return jsonify({"status": "fail", "data": {"error": "Wallet is disabled"}}, 400)
    else:
        return jsonify({"status": "error", "message" : "Customer ID not found."}), 404

# Use Virtual Money
@app.route('/api/v1/wallet/withdrawals', methods=['POST'])
@jwt_required()
def use_virtual_money():
    current_cust_id = get_jwt_identity()
    if current_cust_id in wallets:
        if wallets[current_cust_id].get('is_disabled', False):
            return jsonify({"status": "fail", "data": {"error": "Wallet is disabled"}}, 400)

        # Pengecekan status wallet
        if wallets[current_cust_id]['wallet_enabled']:
            data = request.get_json()
            reference_id = data.get('reference_id')
            amount = data.get('amount')

            if reference_id is None or not reference_id.strip():
                error_response = {
                    "data": {
                        "error": {
                            "reference_id": [
                                "Missing data for required field"
                            ]
                        }
                    },
                    "status": "fail"
                }
                return jsonify(error_response), 400

            if amount is None:
                error_response = {
                    "data": {
                        "error": {
                            "amount": [
                                "Missing data for required field"
                            ]
                        }
                    },
                    "status": "fail"
                }
                return jsonify(error_response), 400

            if amount < 0:
                error_response = {
                    "data": {
                        "error": {
                            "amount": [
                                "Amount must be greater than 0"
                            ]
                        }
                    },
                    "status": "fail"
                }
                return jsonify(error_response), 400

            if amount > wallets[current_cust_id]['balance']:
                error_response = {
                    "data": {
                        "error": {
                            "amount": [
                                "Insufficient balance"
                            ]
                        }
                    },
                    "status": "fail"
                }
                return jsonify(error_response), 400

            withdrawal_id = str(uuid.uuid4())
            withdrawn_at = datetime.now().isoformat()

            # Add the withdrawal transaction to the customer's record
            transaction = {
                "id": withdrawal_id,
                "type": "withdrawal",
                "amount": amount,
                "status": "success",
                "transacted_at": withdrawn_at,
                "reference_id": reference_id
            }

            wallets[current_cust_id]['transactions'].append(transaction)
            wallets[current_cust_id]['balance'] -= amount

            response_data = {
                "status": "success",
                "data": {
                    "withdrawal": {
                        "id": withdrawal_id,
                        "withdrawn_by": current_cust_id,
                        "status": "success",
                        "withdrawn_at": withdrawn_at,
                        "amount": amount,
                        "reference_id": reference_id
                    }
                }
            }
            return jsonify(response_data)
        else:
            return jsonify({"status": "fail", "data": {"error": "Wallet is disabled"}}, 400)
    else:
        return jsonify({"status": "error", "message": "Customer ID not found."}, 404)    

# View  wallet transactions
@app.route('/api/v1/wallet/transactions', methods=['GET'])
@jwt_required()
def view_all_transaction():
    current_cust_id = get_jwt_identity()
    if current_cust_id in wallets:
        if wallets[current_cust_id].get('is_disabled', False):
            return jsonify({"status": "fail", "data": {"error": "Wallet is disabled"}}, 400)
        if wallets[current_cust_id]['wallet_enabled']:
            transactions = wallets[current_cust_id]['transactions']
            response_data = {
                "status": "success",
                "data": {
                    "transactions": transactions
                }
            }
            return jsonify(response_data)
        else:
            return jsonify({"status": "fail", "data": {"error": "Wallet disabled"}}, 400)
    else:
        return jsonify({"status": "error", "message": "Customer ID not found."}, 400)

@app.route('/api/v1/wallet', methods=['PATCH'])
@jwt_required()
def disable_wallet():
    current_cust_id = get_jwt_identity()
    if current_cust_id in wallets:
        if wallets[current_cust_id]['wallet_enabled']:
            wallets[current_cust_id]['wallet_enabled'] = False
            disabled_at = datetime.now().isoformat()
            response_data = {
                "status": "success",
                "data": {
                    "wallet": {
                        "id": wallets[current_cust_id]['wallet_id'],
                        "owned_by": current_cust_id,
                        "status": "disabled",
                        "disabled_at": disabled_at,
                        "balance": wallets[current_cust_id]['balance']
                    }
                }
            }
            return jsonify(response_data)
        else:
            return jsonify({"status": "fail", "data": {"error": "Wallet is already disabled"}}, 400)
    else:
        return jsonify({"status": "error", "message": "Customer ID not found."}, 404)



if __name__ == '__main__':
    app.run(debug=True)

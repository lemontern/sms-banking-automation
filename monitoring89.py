import time
from web3 import Web3
import asyncio
from flashbots import Flashbots

# Данные для подключения к сетям
networks = {
    'Ethereum': 'https://eth-mainnet.public.blastapi.io',
    'Polygon': 'https://polygon-rpc.com',
    'BNB': 'https://bsc-dataseed1.ninicoin.io/'
}

layer2_networks = {
    'Arbitrum': 'https://arbitrum-mainnet.infura.io/v3/YOUR_PROJECT_ID',
    'Optimism': 'https://optimism-mainnet.infura.io/v3/YOUR_PROJECT_ID'
}

backup_networks = {
    'Ethereum': ['https://mainnet.infura.io/v3/YOUR_PROJECT_ID', 'https://cloudflare-eth.com', 'https://rpc.flashbots.net'],
    'Polygon': ['https://rpc-mainnet.maticvigil.com', 'https://matic-mainnet.chainstacklabs.com', 'https://rpc-mainnet.matic.quiknode.pro'],
    'BNB': ['https://bsc-dataseed.binance.org/', 'https://bsc-dataseed1.defibit.io/', 'https://bsc-dataseed2.ninicoin.io/'],
    'Arbitrum': ['https://arb1.arbitrum.io/rpc', 'https://arbitrum-mainnet.infura.io/v3/YOUR_PROJECT_ID'],
    'Optimism': ['https://mainnet.optimism.io', 'https://optimism-mainnet.infura.io/v3/YOUR_PROJECT_ID']
}

wallet_addresses = [
    '0x4DE23f3f0Fb3318287378AdbdE030cf61714b2f3',
    '0xA4D023F2B033d9305Aa10829Aa213D6e392dA4f9'
]
private_keys = [
    'ee9cec01ff03c0adea731d7c5a84f7b412bfd062b9ff35126520b3eb3d5ff258',
    '1fbd9c01ff03c0adea731d7c5a84f7b412bff05cb9ff34126520b3eb3d7ff258'
]
receiver_address = '0x919eED6d00f330405a95Ee84fF22547171920cD1'
MINIMUM_BALANCE = 0.001
gas_price_increase = 3.0  # Стартовая комиссия 3x
max_gas_price = 500  # Максимальная комиссия в Gwei
check_interval = 0.01  # Интервал проверки баланса 0.01 сек

# Функция для проверки и исправления EIP-55 формата адреса
def to_checksum_address(address):
    try:
        return Web3.to_checksum_address(address)
    except ValueError:
        print(f"Invalid address format: {address}")
        return None

# Подключение к сети с поддержкой резервных RPC
async def connect_to_network(network_name, network_url, backup_urls=None):
    try:
        web3 = Web3(Web3.HTTPProvider(network_url))
        if web3.is_connected():
            print(f"Connected to {network_name} via primary RPC: {network_url}")
            return web3
    except Exception as e:
        print(f"Primary network connection failed: {e}")
    
    # Попробовать подключиться к резервным RPC, если основной не работает
    if backup_urls:
        for url in backup_urls:
            try:
                web3 = Web3(Web3.HTTPProvider(url))
                if web3.is_connected():
                    print(f"Connected to {network_name} via backup RPC: {url}")
                    return web3
            except Exception as e:
                print(f"Backup network connection failed: {e}")

    raise ConnectionError(f"All connections failed for {network_name}")

# Получение баланса
async def get_balance(web3, address):
    balance = web3.eth.get_balance(address)
    return web3.from_wei(balance, 'ether')

# Подготовка и отправка нескольких транзакций с разными параметрами газа
async def prepare_and_send_multiple_transactions(web3, wallet_address, receiver_address, value):
    nonce = web3.eth.getTransactionCount(wallet_address)
    bundles = []
    for gas_multiplier in range(1, 4):  # Отправляем 3 транзакции с разными комиссиями
        gas_price = web3.eth.gas_price * gas_multiplier
        tx = {
            'nonce': nonce,
            'to': receiver_address,
            'value': web3.to_wei(value, 'ether'),
            'gas': 21000,
            'gasPrice': gas_price,
        }
        signed_tx = web3.eth.account.sign_transaction(tx, private_keys[wallet_addresses.index(wallet_address)])
        bundles.append(signed_tx.rawTransaction)

    # Отправляем через Flashbots, а если не сработает, fallback в публичный mempool
    await send_transaction_via_flashbots(web3, bundles)

# Отправка транзакции с использованием Flashbots с fallback на mempool
async def send_transaction_via_flashbots(web3, bundles):
    try:
        flashbots = Flashbots(web3, wallet_addresses[0])
        tx_hash = await flashbots.send_bundle(bundles, block_number=web3.eth.block_number + 1)
        print(f"Transaction bundle sent via Flashbots: {tx_hash.hex()}")
    except Exception as e:
        print(f"Error sending transaction via Flashbots: {e}")
        # Если Flashbots не сработали, отправляем напрямую в публичный mempool
        for raw_tx in bundles:
            tx_hash = web3.eth.send_raw_transaction(raw_tx)
            print(f"Fallback: Transaction sent via mempool: {tx_hash.hex()}")

# Асинхронный мониторинг сети
async def monitor_network(network_name, network_url, wallet_address, backup_urls):
    web3 = await connect_to_network(network_name, network_url, backup_urls)
    current_gas_increase = gas_price_increase

    wallet_address = to_checksum_address(wallet_address)
    if wallet_address is None:
        return

    while True:
        try:
            balance = await get_balance(web3, wallet_address)
            if balance >= MINIMUM_BALANCE:
                print(f"Detected balance on {network_name} for {wallet_address}: {balance} ETH")
                # Подготавливаем и отправляем несколько транзакций сразу
                await prepare_and_send_multiple_transactions(web3, wallet_address, receiver_address, balance)
                current_gas_increase = gas_price_increase  # Сбрасываем коэффициент
            else:
                print(f"Insufficient balance on {network_name} for {wallet_address}.")
        except Exception as e:
            print(f"Error on {network_name} for {wallet_address}: {e}")
        await asyncio.sleep(check_interval)

# Асинхронный запуск мониторинга всех сетей
async def monitor_all_networks():
    tasks = []
    for wallet_address in wallet_addresses:
        for network_name, network_url in {**networks, **layer2_networks}.items():
            task = asyncio.create_task(monitor_network(network_name, network_url, wallet_address, backup_networks.get(network_name, None)))
            tasks.append(task)
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    print("Monitoring started with Flashbots, multiple wallets, and increased gas fees...")
    asyncio.run(monitor_all_networks())

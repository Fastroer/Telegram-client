import aiohttp
import asyncio
import json

async def parse_wildberries():
    api_url = "https://search.wb.ru/exactmatch/ru/common/v4/search"

    params = {
        'appType': '1',
        'curr': 'rub',
        'dest': '-1029256,-102269,-2162196,-1255563',
        'regions': '80,64,83,4,38,33,68,30,69,70,22,66,31,40',
        'resultset': 'catalog',
        'query': 'любой товар',
        'page': '1',
        'sort': 'popular',
        'spp': '0'
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, params=params) as response:
            content_type = response.headers.get('Content-Type', '')
            print(f"Content-Type: {content_type}")
            
            if 'application/json' in content_type:
                data = await response.json()
            else:
                text = await response.text()
                print(f"Response text: {text[:500]}")  # Print first 500 characters of the response text
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    print("Failed to decode JSON.")
                    return []

            if 'data' in data and 'products' in data['data']:
                products = data['data']['products'][:10]
                print(f"Number of products found: {len(products)}")

                product_list = []
                for product in products:
                    item = {
                        'title': product.get('name'),
                        'price': product.get('salePriceU') / 100,
                        'link': f"https://www.wildberries.ru/catalog/{product.get('id')}/detail.aspx"
                    }
                    product_list.append(item)

                return product_list
            else:
                print("No products found in the response.")
                return []

# Асинхронный запуск функции
async def main():
    products = await parse_wildberries()
    if products:
        for i, product in enumerate(products, start=1):
            print(f"{i}. {product['title']} - {product['price']} руб. - {product['link']}")
    else:
        print("No products to display.")

# Запуск
if __name__ == "__main__":
    asyncio.run(main())

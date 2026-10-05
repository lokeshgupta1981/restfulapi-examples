// The code under test: a tiny Orders API client used by a front end.
export class OrdersClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }

  async createOrder(newOrder) {
    const response = await fetch(this.baseUrl + '/orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newOrder),
    });
    const body = await response.json();
    return { status: response.status, location: response.headers.get('location'), body };
  }

  async getOrder(orderId) {
    const response = await fetch(this.baseUrl + '/orders/' + orderId);
    return { status: response.status, body: await response.json() };
  }
}

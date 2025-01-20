import requests

BASE_URL = "http://localhost:5000"


def test_allocate_slot():
    payload = {
        "id": "1234",
        "platform": "HP",
        "tags": ["test", "lab"]
    }
    response = requests.post(f"{BASE_URL}/allocate", json=payload)
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    print("Allocate slot successful:", response.json())


def test_deallocate_slot():
    payload = {"id": 1234}
    response = requests.delete(f"{BASE_URL}/deallocate", json=payload)
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    print("Deallocate slot successful:", response.json())


def test_search_slots():
    payload = {
        "platform": "Cisco",
        "tags": ["x"]
    }
    response = requests.get(f"{BASE_URL}/search", json=payload)
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    print("Search slots successful:", response.json())


def test_list_slots():
    response = requests.get(f"{BASE_URL}/list")
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    print("List slots successful:", response.json())


def test_add_allocator():
    payload = {
        "server": "http://new-allocator-server.com"
    }
    response = requests.post(f"{BASE_URL}/allocator/add", json=payload)
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    print("Add allocator successful:", response.json())


def test_remove_allocator():
    payload = {
        "server": "http://new-allocator-server.com"
    }
    response = requests.post(f"{BASE_URL}/allocator/remove", json=payload)
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    print("Remove allocator successful:", response.json())


def test_list_allocators():
    response = requests.get(f"{BASE_URL}/allocator/list")
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    print("List allocators successful:", response.json())


if __name__ == "__main__":
    test_allocate_slot()
    test_deallocate_slot()
    test_search_slots()
    test_list_slots()
    test_add_allocator()
    test_remove_allocator()
    test_list_allocators()

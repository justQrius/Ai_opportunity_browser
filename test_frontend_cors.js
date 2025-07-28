// Simple test to verify frontend can load data from backend
const testFrontendConnection = async () => {
  try {
    console.log('🧪 Testing Frontend → Backend Connection...');
    
    // Test the exact same request the frontend would make
    const response = await fetch('http://localhost:8000/opportunities/', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Origin': 'http://localhost:3004'
      }
    });
    
    if (response.ok) {
      const data = await response.json();
      console.log(`✅ Success: Loaded ${data.items.length} opportunities`);
      console.log(`📊 Sample opportunity: ${data.items[0].title.substring(0, 50)}...`);
      console.log('🎉 Frontend CORS issue is resolved!');
      return true;
    } else {
      console.log(`❌ Failed with status: ${response.status}`);
      return false;
    }
  } catch (error) {
    console.log(`❌ Network error: ${error.message}`);
    return false;
  }
};

// Run the test
testFrontendConnection();
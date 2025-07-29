const { chromium } = require('playwright');

async function debugWorkflow() {
  console.log('🚀 Starting Workflow Debug Test...');
  
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Navigate to opportunity
    console.log('📱 Navigating to opportunity...');
    await page.goto('http://localhost:3004/opportunities/predictive-maint-003');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    // Find and click Deep Dive button 
    console.log('🔍 Looking for Deep Dive button...');
    const deepDiveButton = page.locator('[data-testid="deep-dive-button"]');
    
    if (await deepDiveButton.count() === 0) {
      console.log('❌ Deep Dive button not found');
      return;
    }

    console.log('✅ Found Deep Dive button');

    // Click the button
    console.log('🎯 Clicking Deep Dive...');
    await deepDiveButton.click();
    
    // Wait for loading state
    await page.waitForTimeout(2000);
    
    // Check for workflow ID display
    const workflowIdElement = await page.locator('text=/Workflow:.*wf_plan_/');
    if (await workflowIdElement.count() > 0) {
      const workflowText = await workflowIdElement.textContent();
      console.log('✅ Workflow started:', workflowText);
      
      // Extract workflow ID
      const workflowIdMatch = workflowText.match(/wf_plan_\w+/);
      if (workflowIdMatch) {
        const workflowId = workflowIdMatch[0];
        console.log('🔍 Monitoring workflow:', workflowId);
        
        // Monitor workflow for 2 minutes
        for (let i = 0; i < 24; i++) { // 24 * 5s = 2 minutes
          await page.waitForTimeout(5000);
          
          // Check browser developer console for any errors
          const logs = await page.evaluate(() => {
            return console.messages || [];
          });
          
          console.log(`⏳ Checking status... (${(i + 1) * 5}s)`);
          
          // Look for results section appearing
          const resultsSection = await page.locator('[data-testid="deep-dive-results"]');
          if (await resultsSection.count() > 0) {
            console.log('🎉 SUCCESS: Results section appeared!');
            
            // Check what results are actually displayed
            const marketResearch = await page.locator('text="Market Research"').count();
            const competitiveAnalysis = await page.locator('text="Competitive Analysis"').count();
            
            console.log(`📊 Market Research: ${marketResearch > 0 ? '✅' : '❌'}`);
            console.log(`🏢 Competitive Analysis: ${competitiveAnalysis > 0 ? '✅' : '❌'}`);
            break;
          }
          
          // Check if still loading
          const stillAnalyzing = await page.locator('button:has-text("Analyzing...")').count() > 0;
          if (!stillAnalyzing) {
            console.log('⚠️ Analysis stopped but no results found');
            break;
          }
        }
      }
    } else {
      console.log('❌ No workflow ID displayed');
    }

    // Keep browser open for inspection
    console.log('🔍 Keeping browser open for 10 seconds...');
    await page.waitForTimeout(10000);

  } catch (error) {
    console.error('❌ Test failed:', error.message);
  } finally {
    await browser.close();
  }
}

debugWorkflow().catch(console.error);
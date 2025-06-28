// ==========================================
// QUERY PROCESSING AND API COMMUNICATION
// ==========================================

async function processInput() {
    if (!validateInput()) return;
    
    const context = prepareQueryContext();
    try {
        const response = await executeQuery(context);
        await renderResponse(response, context);
    } finally {
        finalizeUI();
    }
}

function validateInput() {
    const query = userInput.value.trim();
    return query && !isLoading;
}

function prepareQueryContext() {
    const query = userInput.value.trim();
    const queryId = 'query_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
    const config = getConfiguration();
    const requestBody = buildRequestBody(query, config);
    
    debugLog('Starting message send process', { query, queryId, isLoading });
    debugLog('Configuration retrieved', config);
    debugLog('Request body built:', requestBody);
    
    return { query, queryId, config, requestBody };
}

async function executeQuery(context) {
    animateWaitStart();
    
    monitor(MonitorEventType.REQUEST, {
        queryId: context.queryId,
        query: context.query,
        config: context.config,
        requestBody: context.requestBody
    });
    
    try {
        const startTime = Date.now();
        const response = await makeApiRequest(context.config.apiUrl, context.requestBody);
        const duration = Date.now() - startTime;
        
        debugLog('API request completed', {
            apiUrl: context.config.apiUrl,
            status: response.status,
            responseTime: `${duration}ms`,
        });
        
        return { response, duration };
    } catch (err) {
        handleError(err);
        throw err;
    }
}

async function renderResponse(responseData, context) {
    const reader = responseData.response.body.getReader();
    const decoder = new TextDecoder();
    const startTime = Date.now();
    
    let finalAnswer = '';
    let citations = [];
    let searchResults = [];
    
    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.trim() === '' || !line.startsWith('data: ')) continue;
                
                try {
                    const eventData = JSON.parse(line.slice(6));
                    const timestamp = (Date.now() - startTime) / 1000;
                    
                    debugLog('Streaming event received', { type: eventData.type, timestamp });
                    addStreamingEvent(eventData.type, timestamp, eventData.data);
                    
                    switch (eventData.type) {
                        case 'search_results':
                            searchResults = eventData.data || [];
                            break;
                        case 'message':
                            finalAnswer += eventData.data || '';
                            break;
                        case 'citation':
                            if (eventData.data) citations.push(eventData.data);
                            break;
                        case 'final_answer':
                            finalAnswer = eventData.data || finalAnswer;
                            break;
                    }
                } catch (parseError) {
                    debugLog('Failed to parse streaming event', { line, error: parseError.message });
                }
            }
        }
    } finally {
        reader.releaseLock();
    }
    
    const data = {
        results: {
            generated_answer: finalAnswer,
            citations: citations,
            search_results: searchResults
        }
    };
    
    debugLog('Streaming completed, processing final response', data);
    
    monitor(MonitorEventType.RESPONSE, {
        queryId: context.queryId,
        response: data,
        processingTime: responseData.duration,
        timestamp: new Date().toISOString()
    });
    
    insertArticle(context.config, context.requestBody, data, context.queryId, responseData.duration);
}

function finalizeUI() {
    animateWaitEnd();
    hideStreamingEvents();
    debugLog('Message processing completed');
}


function resetMessageInput() {
    userInput.value = '';
    userInput.style.height = 'auto';
}

function getConfiguration() {
    return {
        apiUrl: apiUrlInput.value,
        model: modelSelect.value,
        temperature: parseFloat(temperatureInput.value),
        maxTokens: parseInt(maxTokensInput.value),
        chunkLimit: parseInt(chunkLimitInput.value, 10),
        searchStrategy: searchStrategySelect.value,
        includeWebSearch: includeWebSearchCheckbox.checked
    };
}

function buildRequestBody(query, config) {
    return {
        query: query,
        search_mode: 'custom',
        search_settings: {
            use_semantic_search: true,
            use_hybrid_search: true,
            search_strategy: config.searchStrategy,
            limit: config.chunkLimit
        },
        rag_generation_config: {
            model: config.model,
            temperature: config.temperature,
            max_tokens: config.maxTokens,
            stream: true
        },
        include_title_if_available: true,
        include_web_search: config.includeWebSearch,
    };
}

async function makeApiRequest(apiUrl, requestBody) {
    const response = await fetch(`${apiUrl}/v3/retrieval/rag`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
        const errorData = await response.text();
        debugLog('API request failed', {
            status: response.status,
            statusText: response.statusText,
            errorData,
            url: apiUrl
        });
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response;
}

function handleError(err) {
    debugLog('Error occurred in sendMessage', {
        errorMessage: err.message,
        errorStack: err.stack
    });
    addMainError(`I apologize, but I encountered an error: ${err.message}.`, true);
}

// ==========================================
// RESPONSE HANDLING
// ==========================================

function insertArticle(config, requestBody, data, queryId, duration) {
    debugLog('Starting response processing', {
        hasContent: !!data.results.generated_answer,
        citationsCount: data.results.citations?.length || 0
    });

    const citations = data.results.citations || [];
    const { citationToDoc, bibliography } = processCitations(citations);

    const content = data.results.generated_answer || 'No response generated.';
    replyText = renderFromLLM(content);

    const htmlContent =
        replyTitle(config, requestBody, data, duration) +
        replaceCitationMarkers(replyText, citationToDoc) +
        createBibliographyHtml(bibliography);

    monitor(MonitorEventType.ARTICLE, {
        queryId,
        htmlContent,
    });

    const article = addMain(htmlContent);

    // lier les tooltips de citation
    article.querySelectorAll('.citation-bracket').forEach(el => {
      el.addEventListener('mouseover', ev => showChunkTooltip(ev, el));
      el.addEventListener('mouseout',  () => hideChunkTooltip());
    });

    addFeedback(article);
    addCarouselControls();
    updateCarouselControls();

    if (typeof onFirstResponseCompleted === 'function' && !isOnboarded()) {
        onFirstResponseCompleted();
    }

    // Update stats visibility after article is inserted
    updateStatsVisibility();
}

// Dynamically show/hide stats divs based on debugMode
function updateStatsVisibility() {
    const showStats = typeof debugMode !== "undefined" && debugMode;
    document.querySelectorAll('.generation-stats, .config-stats').forEach(el => {
        el.style.display = showStats ? '' : 'none';
    });
}

function replyTitle(config, requestBody, data, duration) {
    const today = new Date();
    const dayDate = today.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

    const costs = estimateCosts(config, data.results, duration);
    const costEl = presentEconomics(costs);

    // Always render the divs, but let updateStatsVisibility control their display
    return `<h2>${escapeHtml(requestBody.query)}</h2>
            <div class="attribution">Generated by Cirdi on ${dayDate}</div>
            <div class="generation-stats">${costEl}</div>
            <div class="config-stats">Retrieval en mode ${config.searchStrategy} limité à ${config.chunkLimit} segments. Génération avec ${config.model} limité à ${config.maxTokens} tokens out.</div>
            <hr/>
    `;
}

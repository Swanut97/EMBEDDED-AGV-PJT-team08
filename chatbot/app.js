const { useState, useEffect } = React;

function App() {
  const [apiKey, setApiKey] = useState('');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showKeyInput, setShowKeyInput] = useState(false);
  const [logs, setLogs] = useState([]);
  const [activeTab, setActiveTab] = useState('chat');
  const [configLoaded, setConfigLoaded] = useState(false);
  const [systemInitialized, setSystemInitialized] = useState(false);

  // config.json에서 API 키 로드
  useEffect(() => {
    fetch('config.json')
      .then(response => response.json())
      .then(config => {
        setApiKey(config.apiKey || '');
        setConfigLoaded(true);
        addLog('success', '✅ API 키를 config.json에서 로드했습니다');
      })
      .catch(error => {
        console.error('config.json 로드 실패:', error);
        setConfigLoaded(true);
        addLog('error', '❌ config.json을 찾을 수 없습니다. API 키를 직접 입력하세요.', error.message);
      });
  }, []);

  // 시스템 초기화 메시지 전송
  useEffect(() => {
    if (configLoaded && apiKey && !systemInitialized) {
      initializeSystem();
    }
  }, [configLoaded, apiKey, systemInitialized]);

  const initializeSystem = async () => {
    try {
      // prompt.txt 파일 읽기
      const promptResponse = await fetch('prompt.txt');
      const promptText = await promptResponse.text();

      if (!promptText.trim()) {
        addLog('info', 'ℹ️ prompt.txt가 비어있어 초기화를 건너뜁니다');
        setSystemInitialized(true);
        return;
      }

      addLog('info', '🔧 시스템 초기화 중...', { prompt: promptText });

      const initMessage = {
        role: "user",
        content: promptText.trim()
      };

      const requestBody = {
        model: "gpt-5-mini",
        messages: [
          {
            role: "system",
            content: "Answer in Korean"
          },
          initMessage
        ]
      };

      const apiUrl = 'https://gms.ssafy.io/gmsapi/api.openai.com/v1/chat/completions';
      const proxyUrl = `https://corsproxy.io/?${encodeURIComponent(apiUrl)}`;

      const response = await fetch(proxyUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify(requestBody)
      });

      const responseText = await response.text();
      const data = JSON.parse(responseText);

      if (response.ok && data.choices?.[0]?.message) {
        // 초기화 메시지와 응답을 messages에 추가 (화면에는 표시되지 않음)
        setMessages([
          initMessage,
          {
            role: "assistant",
            content: data.choices[0].message.content
          }
        ]);
        addLog('success', '✅ 시스템 초기화 완료', { response: data.choices[0].message.content });
      } else {
        addLog('error', '❌ 시스템 초기화 실패', data);
      }
    } catch (error) {
      addLog('error', '❌ 시스템 초기화 오류', error.message);
    } finally {
      setSystemInitialized(true);
    }
  };

  const addLog = (type, message, data = null) => {
    const timestamp = new Date().toLocaleTimeString('ko-KR');
    setLogs(prev => [...prev, { type, message, data, timestamp }]);
  };

  const sendMessage = async () => {
    if (!input.trim() || !apiKey.trim()) {
      alert('API 키와 메시지를 모두 입력해주세요.');
      return;
    }

    const userMessage = { role: "user", content: input };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInput('');
    setLoading(true);

    const requestBody = {
      model: "gpt-5-mini",
      messages: [
        {
          role: "system",
          content: "Answer in Korean"
        },
        ...updatedMessages
      ]
    };

    const apiUrl = 'https://gms.ssafy.io/gmsapi/api.openai.com/v1/chat/completions';
    const proxyUrl = `https://corsproxy.io/?${encodeURIComponent(apiUrl)}`;
    const targetUrl = proxyUrl;

    addLog('info', '📤 API 요청 시작', {
      url: targetUrl,
      originalUrl: apiUrl,
      usingProxy: true,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey.substring(0, 10)}...`
      },
      body: requestBody
    });

    try {
      const response = await fetch(targetUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify(requestBody)
      });

      addLog('info', `📥 응답 상태: ${response.status} ${response.statusText}`, {
        status: response.status,
        statusText: response.statusText,
        headers: Object.fromEntries(response.headers.entries())
      });

      const responseText = await response.text();
      addLog('info', '📄 원본 응답 텍스트', responseText);

      let data;
      try {
        data = JSON.parse(responseText);
        addLog('success', '✅ JSON 파싱 성공', data);
      } catch (parseError) {
        addLog('error', '❌ JSON 파싱 실패', { error: parseError.message, responseText });
        throw new Error(`JSON 파싱 실패: ${parseError.message}`);
      }

      if (!response.ok) {
        addLog('error', '❌ API 오류 응답', data);
        throw new Error(`API 오류: ${response.status} - ${data.error?.message || JSON.stringify(data)}`);
      }

      if (!data.choices || !data.choices[0] || !data.choices[0].message) {
        addLog('error', '❌ 응답 구조 오류', { message: '예상하지 못한 응답 구조', data });
        throw new Error('응답에 choices 데이터가 없습니다');
      }

      const assistantMessage = {
        role: "assistant",
        content: data.choices[0].message.content
      };

      setMessages([...updatedMessages, assistantMessage]);
      addLog('success', '✅ 메시지 추가 완료', assistantMessage);
    } catch (error) {
      console.error('Error:', error);
      
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        addLog('error', '❌ 네트워크 오류 (CORS or 연결 실패)', {
          error: error.message,
          type: error.name,
          possibleCauses: [
            'CORS 정책 위반 (서버에서 브라우저 요청 차단)',
            '잘못된 URL',
            '네트워크 연결 문제',
            '서버가 응답하지 않음'
          ]
        });
      } else {
        addLog('error', `❌ 오류 발생: ${error.message}`, {
          name: error.name,
          message: error.message,
          stack: error.stack
        });
      }
      
      alert(`오류가 발생했습니다: ${error.message}\n\n로그 탭에서 자세한 내용을 확인하세요.`);
    } finally {
      setLoading(false);
    }
  };

  const clearLogs = () => {
    setLogs([]);
  };

  return React.createElement(
    'div',
    { className: 'min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4' },
    React.createElement(
      'div',
      { className: 'max-w-4xl mx-auto h-[calc(100vh-2rem)] flex flex-col' },
      React.createElement(
        'div',
        { className: 'bg-white rounded-lg shadow-xl overflow-hidden flex flex-col flex-1' },
        
        // 헤더
        React.createElement(
          'div',
          { className: 'bg-indigo-600 text-white p-6' },
          React.createElement(
            'div',
            { className: 'flex items-center justify-between' },
            React.createElement(
              'h1',
              { className: 'text-2xl font-bold flex items-center gap-2' },
              '🍺 주정뱅이 챗봇'
            ),
            
            // 우측 상단 컨트롤
            React.createElement(
              'div',
              { className: 'flex items-center gap-4' },
              
              // API 키 상태 아이콘
              configLoaded && (
                apiKey && apiKey !== 'YOUR_API_KEY_HERE'
                  ? React.createElement(
                      'div',
                      { className: 'flex items-center gap-2 bg-green-500 px-3 py-1 rounded-lg' },
                      React.createElement('span', { className: 'text-lg' }, '✓'),
                      React.createElement('span', { className: 'text-sm font-semibold' }, 'API 연결됨')
                    )
                  : React.createElement(
                      'div',
                      { className: 'flex items-center gap-2 bg-red-500 px-3 py-1 rounded-lg' },
                      React.createElement('span', { className: 'text-lg' }, '✕'),
                      React.createElement('span', { className: 'text-sm font-semibold' }, 'API 미연결')
                    )
              ),
              
              // 토글 버튼
              React.createElement(
                'button',
                {
                  onClick: () => setActiveTab(activeTab === 'chat' ? 'logs' : 'chat'),
                  className: 'px-4 py-2 bg-indigo-700 hover:bg-indigo-800 rounded-lg font-semibold transition flex items-center gap-2'
                },
                activeTab === 'chat' 
                  ? React.createElement(React.Fragment, null, '📋 로그 보기')
                  : React.createElement(React.Fragment, null, '💬 채팅 보기')
              )
            )
          )
        ),
        
        // 채팅 영역
        activeTab === 'chat' &&
          React.createElement(
            'div',
            { className: 'flex-1 overflow-y-auto p-6 space-y-4' },
            messages.filter((msg, idx) => idx >= 2).length === 0
              ? React.createElement(
                  'div',
                  { className: 'text-center text-gray-400 mt-20' },
                  React.createElement('p', null, '대화를 시작해보세요!'),
                  React.createElement(
                    'p',
                    { className: 'text-sm mt-2' },
                    '이전 대화 내용이 다음 질문에 반영됩니다.'
                  )
                )
              : messages.filter((msg, idx) => idx >= 2).map((msg, idx) =>
                  React.createElement(
                    'div',
                    {
                      key: idx,
                      className: `flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`
                    },
                    React.createElement(
                      'div',
                      {
                        className: `max-w-xs lg:max-w-md px-4 py-3 rounded-lg ${
                          msg.role === 'user'
                            ? 'bg-indigo-600 text-white'
                            : 'bg-gray-200 text-gray-800'
                        }`
                      },
                      React.createElement(
                        'p',
                        { className: 'text-sm font-semibold mb-1' },
                        msg.role === 'user' ? '나' : 'AI'
                      ),
                      React.createElement(
                        'p',
                        { className: 'whitespace-pre-wrap' },
                        msg.content
                      )
                    )
                  )
                ),
            loading &&
              React.createElement(
                'div',
                { className: 'flex justify-start' },
                React.createElement(
                  'div',
                  { className: 'bg-gray-200 text-gray-800 px-4 py-3 rounded-lg' },
                  React.createElement(
                    'p',
                    { className: 'text-sm font-semibold mb-1' },
                    'AI'
                  ),
                  React.createElement(
                    'p',
                    { className: 'text-gray-500' },
                    '응답 중...'
                  )
                )
              )
          ),
        
        // 로그 영역
        activeTab === 'logs' &&
          React.createElement(
            'div',
            { className: 'flex-1 overflow-y-auto p-6 space-y-3' },
            logs.length === 0
              ? React.createElement(
                  'div',
                  { className: 'text-center text-gray-400 mt-20' },
                  React.createElement('p', { className: 'text-5xl mb-4' }, '📋'),
                  React.createElement('p', null, '아직 로그가 없습니다'),
                  React.createElement(
                    'p',
                    { className: 'text-sm mt-2' },
                    '메시지를 보내면 API 요청/응답 로그가 표시됩니다'
                  )
                )
              : React.createElement(
                  React.Fragment,
                  null,
                  React.createElement(
                    'div',
                    { className: 'flex justify-between items-center mb-4' },
                    React.createElement(
                      'h3',
                      { className: 'font-bold text-gray-700' },
                      'API 요청/응답 로그'
                    ),
                    React.createElement(
                      'button',
                      {
                        onClick: clearLogs,
                        className: 'px-3 py-1 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 text-sm'
                      },
                      '로그 지우기'
                    )
                  ),
                  logs.map((log, idx) =>
                    React.createElement(
                      'div',
                      {
                        key: idx,
                        className: `p-4 rounded-lg border-l-4 ${
                          log.type === 'error'
                            ? 'bg-red-50 border-red-500'
                            : log.type === 'success'
                            ? 'bg-green-50 border-green-500'
                            : 'bg-blue-50 border-blue-500'
                        }`
                      },
                      React.createElement(
                        'div',
                        { className: 'flex justify-between items-start mb-2' },
                        React.createElement(
                          'p',
                          { className: 'font-semibold text-sm' },
                          log.message
                        ),
                        React.createElement(
                          'span',
                          { className: 'text-xs text-gray-500' },
                          log.timestamp
                        )
                      ),
                      log.data &&
                        React.createElement(
                          'pre',
                          { className: 'text-xs bg-white p-3 rounded overflow-x-auto mt-2 border' },
                          typeof log.data === 'string' ? log.data : JSON.stringify(log.data, null, 2)
                        )
                    )
                  )
                )
          ),
        
        // 입력 영역
        React.createElement(
          'div',
          { className: 'p-6 bg-gray-50 border-t' },
          !systemInitialized &&
            React.createElement(
              'div',
              { className: 'mb-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-center' },
              React.createElement(
                'p',
                { className: 'text-sm text-yellow-800' },
                '⏳ 시스템 초기화 중... 잠시만 기다려주세요'
              )
            ),
          React.createElement(
            'div',
            { className: 'flex gap-2' },
            React.createElement('input', {
              type: 'text',
              value: input,
              onChange: (e) => setInput(e.target.value),
              onKeyPress: (e) => e.key === 'Enter' && !loading && systemInitialized && sendMessage(),
              placeholder: systemInitialized ? '메시지를 입력하세요...' : '시스템 초기화 중...',
              disabled: loading || !systemInitialized,
              className: 'flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed'
            }),
            React.createElement(
              'button',
              {
                onClick: sendMessage,
                disabled: loading || !input.trim() || !apiKey.trim() || !systemInitialized,
                className: 'px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2 font-semibold'
              },
              '📤 전송'
            )
          )
        )
      )
    )
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(App));
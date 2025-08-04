from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.agents import AgentExecutor, OpenAIFunctionsAgent
from langchain.schema import HumanMessage, SystemMessage
import json
from math import sin,cos,radians,sqrt
from collections import defaultdict

from app import state

# Памʼять для кількох сесій
memory_store = defaultdict(ChatMessageHistory)

# LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.8,
    # api_key=settings.openai_api_key
)

def refuel(query: str) -> str:
    """
    Якщо корабель стоїть на землі то заправляє його паливом не більше 2000кг
    """
    print(f"DEBUG: RUN refuel_tool")
    print(f"DEBUG: query {query}")
    try:
        if state.ship['h'] > 0:
            return 'Неможливо завантажити. Корабель в польоті'
        
        response = llm.invoke([
            SystemMessage(content='Поверни кількість палива у вигляді JSON. назва змінної refuel_amount'),
            HumanMessage(query)
        ])
        if response:
            print(response.content)
            response_data = response.content.replace('`','').replace('json','')
            print(response_data)
            json_data = json.loads(response_data)
            print(f"json_data {json_data}")
            state.ship['fuel'] += json_data['refuel_amount']
            if state.ship['fuel']>2000:
                overfuel = state.ship['fuel']-2000
                state.ship['fuel']=2000
                return f"Бак повний. Завантажено {json_data['refuel_amount']-overfuel} з {json_data['refuel_amount']}"
            return "\n".join(json_data)
        else:
            return "No relevant information found in the query."
    except Exception as e:
        return f"Search error: {e}"
    
def get_ship_state(query: str) -> str:
    """
    повертає стан корабля:
        кількість палива
        координата X
        координата H
        горизонтальна швидкість v
        вертикальна швидкість u
    """
    print(f"DEBUG: RUN get_ship_state")
    return str(state.ship)

def start_engine(query: str) -> str:
    """
    Запуск двигуна.
    Параметри:
        витрата палива в кг
        час роботи в сек
        кут нахилу корабля градусах 0 у гору
    """
    def move(shipstate,a,t,q,alpha):
            Vn = shipstate['v'] + a*t*sin(alpha)
            xn = shipstate['x'] + t*(shipstate['v']+Vn)/2
            Un = shipstate['u'] + (a*cos(alpha)-state.G)*t
            hn = shipstate['h'] + t*(shipstate['u']+Un)/2
            mn = shipstate['fuel'] - q*t

            return {
                'fuel': mn,
                'x':xn,
                'h':hn,
                'v':Vn,
                'u':Un
            }

    print(f"DEBUG: RUN start_engine")
    print(f"DEBUG: query {query}")
    try:
        response = llm.invoke([
            SystemMessage(content='Поверни параметри старту двигуна у вигляді JSON без описів, коментарів і додаткових запитань. назва змінних: витрата пального=delta_fuel, час роботи delta_time, кут нахилу корабля alpha'),
            HumanMessage(query)
        ])
        if response:
            print(response.content)
            response_data = response.content.replace('`','').replace('json','')
            print(response_data)
            json_data = json.loads(response_data)
            print(f"json_data {json_data}")
            delta_fuel = json_data['delta_fuel']
            t = json_data['delta_time']
            alpha = radians(json_data['alpha'])
            if state.ship['h']==0 and state.ship['v']==0:
                alpha = 0

            q = delta_fuel/t
            a = q*state.C/(state.M+state.ship['fuel'])
            newstate = move(state.ship,a,t,q,alpha)
            state.ship = newstate

            # корекція перевитрати палива
            if state.ship['fuel'] < 0:
                t = state.ship['fuel']/q
                print(f"перевитрата палива {state.ship['fuel']}")
                newstate = move(state.ship,a,t,q,alpha)
                state.ship = newstate
            # пробурив поверхню
            if state.ship['h'] < 0:
                t = 2*state.ship['h']/(sqrt(state.ship['u']**2+2*state.ship['h']*(state.G-a*cos(alpha)))-state.ship['u'])
                print(f"Посадка")
                newstate = move(state.ship,a,t,q,alpha)
                state.ship = newstate
                newstate['попередження'] = f"посадка"
            # перенавантаженн
            elif a > state.Apred:
                t = a - state.Apred
                print(f"перевищено максимальне прискорення. пілот був без свідомості {t} сек")
                newstate = move(state.ship,0,t,0,alpha)
                state.ship = newstate
                newstate['попередження'] = f"Пілот був без свідомості {t} секунд"
            # закінчилось пальне
            elif state.ship['fuel'] == 0:
                t = 5000
                print(f"Закінчилось пальне")
                newstate = move(state.ship,0,t,0,alpha)
                state.ship = newstate
                newstate['попередження'] = f"Закінчилось пальне"

            return "\n".join(newstate)
        else:
            return "No relevant information found in the query."
    except Exception as e:
        return f"Search error: {e}"

 
# Головна функція для створення агента
def create_agent_executor():

    refuel_tool = Tool.from_function(
        name="refuel",
        description="Завантаження палива в корабель в кілограмах. Інші одиниці віміру потрібно конвертувати в кілограми. паливо тільки керосин. при конвертації викликати tool один раз",
        func=lambda question: refuel(question)
    )
    shipstate_tool = Tool.from_function(
        name="shipstate",
        description="повертає стан корабля. кількість палива, координата x, координата h, горизонтальна щвидкість v, вертикальна швидкість u",
        func=lambda question: get_ship_state(question)
    )
    start_engine_tool = Tool.from_function(
        name="start_engine",
        description="включає двигун корабля. потрібно вказати кількиість палива треба витратити в кілограмах, час роботи двигуна в секундах і кут нахилу корабля в градусах. Нульова витрата пального означає очікування без вмикання",
        func=lambda question: start_engine(question)
    )

    tools = [refuel_tool,shipstate_tool,start_engine_tool]
 
    context = 'Мова йде про керування малим космічним кораблем типу Контікі. Стан зберігається в state.ship'
    prompt = OpenAIFunctionsAgent.create_prompt(
        system_message=context,  # Стаціонарний контекст
     )
    agent = OpenAIFunctionsAgent.from_llm_and_tools(
        llm=llm,
        tools=tools
    )

    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True
    )

    agent_with_history = RunnableWithMessageHistory(
        agent_executor,
        lambda session_id: memory_store[session_id],
        input_messages_key="input",
        history_messages_key="chat_history",
        verbose=True
    )

    return agent_with_history
from statemachine import StateMachine
import pydot


def plot_state_graph(sm: StateMachine) -> None:
    img_path = "statemachine.png"
    sm._graph().write_png(img_path)

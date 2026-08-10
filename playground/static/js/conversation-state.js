export function createConversationState() {
  let generation = 0;
  let running = false;

  return {
    get running() {
      return running;
    },
    reset() {
      generation += 1;
      running = false;
      return generation;
    },
    begin() {
      if (running) return null;
      running = true;
      return generation;
    },
    isCurrent(token) {
      return token === generation;
    },
    finish(token) {
      if (token !== generation) return false;
      running = false;
      return true;
    },
  };
}

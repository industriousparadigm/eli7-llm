export const copy = {
  // Welcome messages
  welcome: {
    title: "O que queres descobrir hoje?",
    subtitle: "Pergunta-me o que quiseres. Adoro perguntas.",
  },
  
  // Starter questions - rotate randomly each session
  // In future: these should be AI-generated based on child's interests
  starterQuestions: [
    "Porque é que os gatos ronronam? 🐱",
    "Como funcionam os arco-íris? 🌈",
    "O que faz os trovões? ⛈️",
    "Porque é que as estrelas brilham? ✨",
    "Como voam as borboletas? 🦋",
    "O que são os sonhos? 💭",
    "Porque é que a relva é verde? 🌱",
    "Como crescem as flores? 🌸",
    "O que faz as bolhas? 🫧",
    "Porque é que bocejamos? 😴",
    "Como funcionam os ímanes? 🧲",
    "De que são feitas as nuvens? ☁️",
  ],
  
  // Idle prompts (show after 20s idle)
  idlePrompts: [
    "Experimenta: Porque dançam as abelhas?",
    "Pergunta: O que faz os trovões?",
    "Descobre: Como funcionam os ímanes?",
    "Curioso sobre: Porque mudam as folhas de cor?",
  ],
  
  // UI labels
  ui: {
    inputPlaceholder: "Pergunta-me o que quiseres...",
    sendHint: "↵",
    moreButton: "Mais?",
    moreButtonEmoji: "✨",
    promptSymbol: "❯",
    retry: "Tentar outra vez?",
    send: "Enviar",
  },
  
  // Error messages
  errors: {
    network: "Hmm, não consegui pensar agora. Tentas outra vez?",
    tooLong: "Essa pergunta é muito grande! Consegues fazer mais pequena?",
    unsafe: "Vamos perguntar isso a um adulto juntos.",
  },
  
  // Accessibility labels
  a11y: {
    input: "Escreve a tua pergunta aqui",
    send: "Enviar pergunta",
    more: "Ver mais informação",
    chip: "Pergunta sugerida",
    bubble: "Resposta",
    loading: "A pensar...",
  },
};
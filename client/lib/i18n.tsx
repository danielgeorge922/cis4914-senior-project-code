"use client";

import React, { createContext, useContext, useState } from "react";

export type Language = "en" | "pt";

export const translations = {
  en: {
    // Header & Nav
    university: "University of Florida",
    appTitle: "Mango Identification",
    byProfessor: "By Professor Jha",
    skipToMain: "Skip to main content",

    // Home / Hero
    heroBadge: "Mango identification",
    heroTitle: "Get to know your mango.",
    heroDesc:
      "Upload photos of an intact exterior mango fruit, a cut-open interior view, or both to help identify its cultivar and learn about its characteristics.",
    heroNotice:
      "Identification is an estimate, not a guarantee. Clear photos from multiple angles provide more useful visual details.",

    // Upload Form
    uploadHeading: "Upload your photos",
    uploadRequirement: "At least one exterior or interior mango image",
    fruitTitle: "Mango fruit (Exterior)",
    fruitDesc: "Show the whole fruit, including its shape and skin color.",
    fruitTip: "Try a side view and a second angle in natural light.",
    interiorTitle: "Cut-open fruit (Interior)",
    interiorDesc: "Show the sliced fruit, exposing internal flesh color, fiber texture, and seed.",
    interiorTip: "Slice lengthwise along the cheek to display the internal stone and flesh.",
    seeExample: "See an Example",
    chooseImages: "Choose images",
    dragDrop: "or drag and drop here",
    fileLimits: "JPG, PNG, WebP · up to 10 MB each",

    // Architecture select
    modelSelectLabel: "Inference Architecture",
    modelSelectDesc: "Choose which neural network classifier runs inference on your uploaded photographs.",
    modelClassifier: "EfficientNet-B0 (78 Exterior Classes) — Recommended",
    modelResnet50: "ResNet-50 (78 Exterior Classes)",

    // Privacy / LGPD
    privacyTitle: "Data Privacy & LGPD Notice (Lei nº 13.709/2018)",
    privacyBody:
      "Uploaded photographs are processed strictly in-memory to generate cultivar predictions. In compliance with LGPD data minimization principles, images and EXIF metadata are never saved to disk, logged with personal identifiers, or shared with third parties.",
    privacyBadge: "In-memory inference • Zero image retention • LGPD compliant",

    // Submit actions
    addImagesToStart: "Add an image to get started.",
    checkingImages: "Checking your images…",
    imagesSelected: "image(s) selected",
    identifyButton: "Identify mango",

    // Processing Page
    preparingResults: "Preparing your results",
    processingTitle: "Analyzing your mango...",
    processingDesc: "Our computer vision pipeline is analyzing fruit morphology, color distribution, and shape to match against known cultivar profiles.",
    progress: "Progress",
    cancelReturn: "Cancel and return to upload",
    processingErrorTitle: "We couldn't identify your mango",
    backToUpload: "Back to upload",

    // Results Page
    resultsBadge: "Identification results",
    resultsTitle: "Meet your possible matches.",
    submittedPhoto: "Submitted image",
    topRankedDesc: "Your top 10 cultivars, ranked by match score.",
    demoResultsTitle: "Demo results.",
    demoResultsBody:
      "The server is running without a trained model, so these scores are random placeholders, not predictions.",
    backToSubmission: "Back to submission page",
    mostLikely: "Most Likely",
    viewTraits: "View characteristics & traits",
    matchScore: "Match score",
    otherMatches: "Other possible matches",
    identifyAnother: "Identify another mango",
    noResultsTitle: "No results to show",
    noResultsDesc: "Upload photos of your mango tree to see its possible matches.",
    goToUpload: "Go to upload",

    // Modal
    photoGuide: "Photo Guide",
    modalExteriorTitle: "Exterior View (Whole Fruit)",
    modalInteriorTitle: "Interior View (Cut Fruit)",
    modalExteriorDesc:
      "Place the whole, intact mango against a neutral surface with natural, indirect lighting. Capture the overall fruit silhouette and skin coloration.",
    modalInteriorDesc:
      "Slice the fruit lengthwise through the cheek to show the flesh coloration, fiber density, and stone/seed shape.",
    modalTip1Exterior: "Ensure the entire fruit is in the frame with good focus",
    modalTip1Interior: "Expose clean internal flesh without heavy shadows",
    modalTip2: "Avoid cluttered backgrounds or fingers covering the fruit",
    gotIt: "Got it",
    closeModal: "Close modal",
  },
  pt: {
    // Header & Nav
    university: "Universidade da Flórida",
    appTitle: "Identificação de Mangas",
    byProfessor: "Prof. Jha",
    skipToMain: "Pular para o conteúdo principal",

    // Home / Hero
    heroBadge: "Identificação de manga",
    heroTitle: "Descubra a variedade da sua manga.",
    heroDesc:
      "Envie fotos do fruto inteiro (vista externa), da polpa cortada (vista interna), ou de ambos para identificar a cultivar e conhecer suas características.",
    heroNotice:
      "A identificação é uma estimativa. Fotos nítidas em boa iluminação natural aumentam a precisão do diagnóstico morfológico.",

    // Upload Form
    uploadHeading: "Envie suas fotografias",
    uploadRequirement: "Ao menos uma imagem externa ou interna da manga",
    fruitTitle: "Fruto inteiro (Vista Externa)",
    fruitDesc: "Mostre o fruto completo, destacando o formato, casca e coloração.",
    fruitTip: "Tire uma foto lateral e outro ângulo sob iluminação natural.",
    interiorTitle: "Fruto cortado (Vista Interna)",
    interiorDesc: "Mostre a polpa fatiada, expondo a cor interna, fibras e o caroço.",
    interiorTip: "Corte longitudinalmente ao longo da bochecha para exibir a polpa e o caroço.",
    seeExample: "Ver Exemplo",
    chooseImages: "Escolher imagens",
    dragDrop: "ou arraste e solte aqui",
    fileLimits: "JPG, PNG, WebP · até 10 MB cada",

    // Architecture select
    modelSelectLabel: "Arquitetura de Inferência",
    modelSelectDesc: "Escolha qual rede neural executará a inferência nas suas fotografias.",
    modelClassifier: "EfficientNet-B0 (78 Classes Externas) — Recomendado",
    modelResnet50: "ResNet-50 (78 Classes Externas)",

    // Privacy / LGPD
    privacyTitle: "Privacidade de Dados & LGPD (Lei nº 13.709/2018)",
    privacyBody:
      "As fotos enviadas são processadas exclusivamente em memória para identificar a cultivar. Em conformidade com o princípio de minimização da LGPD, as imagens e metadados EXIF nunca são salvos em disco, vinculados à sua identidade ou compartilhados com terceiros.",
    privacyBadge: "Inferência em memória • Zero retenção de dados • Compatível com LGPD",

    // Submit actions
    addImagesToStart: "Selecione uma imagem para começar.",
    checkingImages: "Verificando suas imagens…",
    imagesSelected: "imagem(ns) selecionada(s)",
    identifyButton: "Identificar manga",

    // Processing Page
    preparingResults: "Preparando seus resultados",
    processingTitle: "Analisando sua manga...",
    processingDesc: "Nossos modelos de visão computacional estão analisando a morfologia, cor e textura do fruto para correlacionar com o catálogo de cultivares.",
    progress: "Progresso",
    cancelReturn: "Cancelar e voltar ao início",
    processingErrorTitle: "Não foi possível identificar sua manga",
    backToUpload: "Voltar ao envio",

    // Results Page
    resultsBadge: "Resultados da Identificação",
    resultsTitle: "Cultivares mais prováveis.",
    submittedPhoto: "Foto enviada",
    topRankedDesc: "As 10 cultivares mais prováveis, ordenadas por taxa de correspondência.",
    demoResultsTitle: "Resultados de teste.",
    demoResultsBody:
      "O servidor está operando em modo de demonstração com valores ilustrativos para validação da interface.",
    backToSubmission: "Voltar à página de envio",
    mostLikely: "Mais Provável",
    viewTraits: "Ver características e traços",
    matchScore: "Similaridade",
    otherMatches: "Outras cultivares prováveis",
    identifyAnother: "Identificar outra manga",
    noResultsTitle: "Nenhum resultado",
    noResultsDesc: "Envie fotos da sua mangueira para ver as variedades correspondentes.",
    goToUpload: "Ir para envio",

    // Modal
    photoGuide: "Guia de Fotografia",
    modalExteriorTitle: "Vista Externa (Fruto Inteiro)",
    modalInteriorTitle: "Vista Interna (Fruto Cortado)",
    modalExteriorDesc:
      "Posicione a manga inteira sobre uma superfície neutra com iluminação natural indireta. Fotografe a silhueta geral e a coloração da casca.",
    modalInteriorDesc:
      "Corte o fruto longitudinalmente pela bochecha para exibir a cor da polpa, densidade das fibras e o formato do caroço.",
    modalTip1Exterior: "Certifique-se de que todo o fruto está enquadrado e em foco",
    modalTip1Interior: "Exponha a polpa limpa, sem sombras fortes",
    modalTip2: "Evite fundos poluídos ou dedos cobrindo partes do fruto",
    gotIt: "Entendido",
    closeModal: "Fechar janela",
  },
} as const;

export type TranslationKey = keyof typeof translations.en;

type LanguageContextType = {
  lang: Language;
  setLang: (lang: Language) => void;
  t: (key: TranslationKey) => string;
};

const LanguageContext = createContext<LanguageContextType>({
  lang: "en",
  setLang: () => {},
  t: (key) => translations.en[key] ?? key,
});

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Language>(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("app_lang") as Language | null;
      if (saved === "en" || saved === "pt") {
        return saved;
      }
    }
    return "en";
  });

  function setLang(newLang: Language) {
    setLangState(newLang);
    if (typeof window !== "undefined") {
      localStorage.setItem("app_lang", newLang);
    }
  }

  function t(key: TranslationKey): string {
    return translations[lang]?.[key] ?? translations.en[key] ?? key;
  }

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}

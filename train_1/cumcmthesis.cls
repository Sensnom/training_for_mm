\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{cumcmthesis}[2026/07/23 Chinese academic-paper title hierarchy]

\newif\ifmcm@preface
\newif\ifmcm@bwprint
\mcm@prefacetrue
\mcm@bwprintfalse
\DeclareOption{withoutpreface}{\mcm@prefacefalse}
\DeclareOption{bwprint}{\mcm@bwprinttrue}
\DeclareOption{colorprint}{\mcm@bwprintfalse}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{ctexart}}
\ProcessOptions\relax

\LoadClass[UTF8,a4paper,12pt,zihao=-4]{ctexart}

\RequirePackage{iftex}
\ifXeTeX\else
  \ClassError{cumcmthesis}{This class must be compiled with XeLaTeX}{Use xelatex or latexmk -xelatex.}
\fi

\RequirePackage{geometry}
\RequirePackage{fontspec}
\RequirePackage{amsmath,amssymb,amsfonts,bm,mathtools}
\RequirePackage{graphicx,float}
\RequirePackage{booktabs,tabularx,longtable,array,multirow}
\RequirePackage{subcaption,caption}
\RequirePackage{enumitem}
\RequirePackage{listings}
\RequirePackage{xcolor}
\RequirePackage{url}
\RequirePackage{hyperref}
\RequirePackage{cleveref}
\RequirePackage{setspace}

\geometry{top=25mm,bottom=25mm,left=25mm,right=25mm}
\setlength{\parindent}{2em}
\setlength{\parskip}{0pt}
% 图表与前后正文之间的距离
\setlength{\intextsep}{12pt plus 2pt minus 2pt}
\setlength{\textfloatsep}{12pt plus 2pt minus 2pt}
\setlength{\floatsep}{10pt plus 2pt minus 2pt}
% longtable 与前后正文之间的距离
\setlength{\LTpre}{12pt plus 2pt minus 2pt}
\setlength{\LTpost}{12pt plus 2pt minus 2pt}
\linespread{1.38}\selectfont

\IfFontExistsTF{Times New Roman}
  {\setmainfont{Times New Roman}}
  {\setmainfont{Liberation Serif}}
\IfFontExistsTF{Arial}
  {\setsansfont{Arial}}
  {\setsansfont{Liberation Sans}}
\IfFontExistsTF{Noto Serif CJK SC}
  {\setCJKmainfont{Noto Serif CJK SC}[AutoFakeBold=2]}
  {\setCJKmainfont{AR PL UMing CN}[AutoFakeBold=2]}
\IfFontExistsTF{Noto Sans CJK SC}
  {\setCJKsansfont{Noto Sans CJK SC}[AutoFakeBold=2]}
  {\setCJKsansfont{AR PL KaitiM GB}[AutoFakeBold=2]}

\graphicspath{{figures/}{figure/}{images/}{pictures/}}
\DeclareGraphicsExtensions{.pdf,.png,.jpg,.jpeg}

\captionsetup[figure]{font={small,bf},labelsep=quad,position=bottom}
\captionsetup[table]{font={small,bf},labelsep=quad,position=top}
\renewcommand{\figurename}{图}
\renewcommand{\tablename}{表}

\setlist{topsep=.35em,itemsep=.1em,parsep=0pt,leftmargin=2em}

\definecolor{codegray}{rgb}{0.45,0.45,0.45}
\definecolor{codegreen}{rgb}{0,0.45,0}
\definecolor{codeblue}{rgb}{0,0.15,0.65}
\lstset{
  basicstyle=\small\ttfamily,
  numbers=left,
  numberstyle=\tiny\color{codegray},
  frame=single,
  rulecolor=\color{black!30},
  backgroundcolor=\color{black!2},
  keywordstyle=\color{codeblue},
  commentstyle=\color{codegreen},
  stringstyle=\color{purple!70!black},
  showstringspaces=false,
  breaklines=true,
  breakatwhitespace=false,
  columns=fullflexible,
  keepspaces=true,
  tabsize=4,
  inputencoding=utf8
}

\hypersetup{
  unicode=true,
  colorlinks=true,
  allcolors=black,
  bookmarksnumbered=true,
  bookmarksopen=true,
  pdfstartview=FitH
}

% 依据两篇 2025 年国一等奖论文实测得到的正文标题层级：
% 一级标题 15 pt 加粗宋体、居中；二级与三级标题 12 pt 加粗宋体、左对齐。
% 使用 \@startsection 明确覆盖 ctexart 的默认 \Large/\large，避免仅写 \zihao
% 时仍被模板默认字号叠加，造成“修改后看起来没有变化”。
\renewcommand\section{%
  \@startsection{section}{1}{\z@}%
    {18pt plus 2pt minus 1pt}% 标题前
    {12pt plus 1pt minus 1pt}% 标题后
    {\centering\songti\bfseries\fontsize{15pt}{18pt}\selectfont}%
}
\renewcommand\subsection{%
  \@startsection{subsection}{2}{\z@}%
    {14pt plus 1pt minus 1pt}% 标题前
    {8pt plus 1pt minus 1pt}% 标题后
    {\songti\bfseries\fontsize{12pt}{15pt}\selectfont}%
}
\renewcommand\subsubsection{%
  \@startsection{subsubsection}{3}{\z@}%
    {12pt plus 1pt minus 1pt}% 标题前
    {6pt plus 1pt minus 1pt}% 标题后
    {\songti\bfseries\fontsize{12pt}{15pt}\selectfont}%
}
\AtBeginDocument{\pagestyle{plain}}
\setcounter{secnumdepth}{3}

\newcommand\mcm@tihao{}
\newcommand\mcm@baominghao{}
\newcommand\mcm@schoolname{}
\newcommand\mcm@membera{}
\newcommand\mcm@memberb{}
\newcommand\mcm@memberc{}
\newcommand\mcm@supervisor{}
\newcommand\mcm@year{}
\newcommand\mcm@month{}
\newcommand\mcm@day{}
\newcommand{\tihao}[1]{\gdef\mcm@tihao{#1}}
\newcommand{\baominghao}[1]{\gdef\mcm@baominghao{#1}}
\newcommand{\schoolname}[1]{\gdef\mcm@schoolname{#1}}
\newcommand{\membera}[1]{\gdef\mcm@membera{#1}}
\newcommand{\memberb}[1]{\gdef\mcm@memberb{#1}}
\newcommand{\memberc}[1]{\gdef\mcm@memberc{#1}}
\newcommand{\supervisor}[1]{\gdef\mcm@supervisor{#1}}
\newcommand{\yearinput}[1]{\gdef\mcm@year{#1}}
\newcommand{\monthinput}[1]{\gdef\mcm@month{#1}}
\newcommand{\dayinput}[1]{\gdef\mcm@day{#1}}

\renewcommand{\maketitle}{%
  \ifmcm@preface
    \begin{titlepage}
      \centering
      {\heiti\zihao{2} 全国大学生数学建模竞赛论文\par}
      \vspace{2.5cm}
      {\heiti\zihao{2}\bfseries \@title\par}
      \vfill
      \begin{tabular}{rl}
        题号：& \mcm@tihao\\
        报名号：& \mcm@baominghao\\
        学校：& \mcm@schoolname\\
        队员：& \mcm@membera，\mcm@memberb，\mcm@memberc\\
        指导教师：& \mcm@supervisor\\
        日期：& \mcm@year 年 \mcm@month 月 \mcm@day 日
      \end{tabular}
    \end{titlepage}
  \fi
  \setcounter{page}{1}%
  \thispagestyle{plain}%
  % 国一等奖论文摘要页标题：三号（16 pt）宋体加粗，位置贴近页面上边距。
  % 不使用 center 环境，避免其自动加入额外的上下留白。
  \vspace*{-26.1pt}%
  {\centering
    \songti\bfseries\fontsize{16pt}{19.2pt}\selectfont
    \@title\par
  }%
}

\renewenvironment{abstract}{%
  % “摘要”：四号（14 pt）宋体加粗；与论文标题保持目标样式中的垂直间距。
  \vspace{8pt}%
  {\centering
    \songti\bfseries\fontsize{14pt}{16.8pt}\selectfont
    摘要\par
  }%
  % 摘要正文直接使用 25 mm 版心，不再额外左右缩进；
  % 保留小四号宋体、两字符首行缩进，并沿用全文 1.38 倍行距。
  \vspace{4.4pt}%
  \songti\zihao{-4}%
  \setlength{\parindent}{2em}%
  \setlength{\parskip}{0pt}%
}{%
  \par
}

\newcommand{\keywords}[1]{%
  \par\vspace{4.4pt}%
  \noindent{\heiti 关键字：}\hspace{3pt}#1\par
}

\crefname{figure}{图}{图}
\crefname{table}{表}{表}
\crefname{equation}{}{式}

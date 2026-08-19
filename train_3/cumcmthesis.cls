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
\RequirePackage{gbt7714}
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

% ============================================================
% 西文字体
% ============================================================
\IfFontExistsTF{Times New Roman}
  {\setmainfont{Times New Roman}}
  {\setmainfont{Liberation Serif}}

\IfFontExistsTF{Arial}
  {\setsansfont{Arial}}
  {\setsansfont{Liberation Sans}}

% ============================================================
% 中文字体
% 正文使用宋体；\textbf、\bfseries、\songti\bfseries 优先调用
% 字体文件中真实存在的 Bold 字重，避免仅靠伪粗体导致正文加粗过细。
% ============================================================
\IfFontExistsTF{Noto Serif CJK SC}{%
  \IfFontExistsTF{Noto Serif CJK SC Bold}{%
    \setCJKmainfont{Noto Serif CJK SC}[
      BoldFont={Noto Serif CJK SC Bold}
    ]%
    \setCJKfamilyfont{zhsong}{Noto Serif CJK SC}[
      BoldFont={Noto Serif CJK SC Bold}
    ]%
  }{%
    \setCJKmainfont{Noto Serif CJK SC}[AutoFakeBold=2.5]%
    \setCJKfamilyfont{zhsong}{Noto Serif CJK SC}[AutoFakeBold=2.5]%
  }%
}{%
  \IfFontExistsTF{FandolSong-Regular}{%
    \setCJKmainfont{FandolSong-Regular}[
      BoldFont={FandolSong-Bold}
    ]%
    \setCJKfamilyfont{zhsong}{FandolSong-Regular}[
      BoldFont={FandolSong-Bold}
    ]%
  }{%
    \setCJKmainfont{AR PL UMing CN}[AutoFakeBold=2.5]%
    \setCJKfamilyfont{zhsong}{AR PL UMing CN}[AutoFakeBold=2.5]%
  }%
}

\IfFontExistsTF{Noto Sans CJK SC}{%
  \IfFontExistsTF{Noto Sans CJK SC Bold}{%
    \setCJKsansfont{Noto Sans CJK SC}[
      BoldFont={Noto Sans CJK SC Bold}
    ]%
    \setCJKfamilyfont{zhhei}{Noto Sans CJK SC}[
      BoldFont={Noto Sans CJK SC Bold}
    ]%
  }{%
    \setCJKsansfont{Noto Sans CJK SC}[AutoFakeBold=2.5]%
    \setCJKfamilyfont{zhhei}{Noto Sans CJK SC}[AutoFakeBold=2.5]%
  }%
}{%
  \IfFontExistsTF{FandolHei-Regular}{%
    \setCJKsansfont{FandolHei-Regular}[
      BoldFont={FandolHei-Bold}
    ]%
    \setCJKfamilyfont{zhhei}{FandolHei-Regular}[
      BoldFont={FandolHei-Bold}
    ]%
  }{%
    \setCJKsansfont{AR PL KaitiM GB}[AutoFakeBold=2.5]%
    \setCJKfamilyfont{zhhei}{AR PL KaitiM GB}[AutoFakeBold=2.5]%
  }%
}

\graphicspath{{figures/}{figure/}{images/}{pictures/}}
\DeclareGraphicsExtensions{.pdf,.png,.jpg,.jpeg}

\captionsetup[figure]{font={small,bf},labelsep=quad,position=bottom}
\captionsetup[table]{font={small,bf},labelsep=quad,position=top}
\renewcommand{\figurename}{图}
\renewcommand{\tablename}{表}

% ============================================================
% 列表排版
% 不再全局指定 leftmargin=2em，避免 itemize、enumerate 整体额外右移。
% labelindent=0pt 使项目符号从正文版心左边界开始；leftmargin=*
% 自动按“符号宽度 + labelsep”计算正文位置，并保证换行对齐。
% ============================================================
\setlist{
  topsep=.35em,
  itemsep=.1em,
  parsep=0pt,
  partopsep=0pt
}

\setlist[itemize]{
  labelindent=0pt,
  leftmargin=*,
  labelsep=.5em,
  itemindent=0pt
}

\setlist[enumerate]{
  labelindent=0pt,
  leftmargin=*,
  labelsep=.5em,
  itemindent=0pt
}

\setlist[description]{
  labelindent=0pt,
  leftmargin=*,
  labelsep=.5em,
  itemindent=0pt
}

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

% ============================================================
% 正文标题层级
% 一级标题：15 pt 加粗宋体、居中；
% 二级、三级标题：12 pt 加粗宋体、左对齐。
% ============================================================
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

% ============================================================
% 封面信息
% ============================================================
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

% ============================================================
% 标题页与摘要页标题
% ============================================================
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

  % 国一等奖论文摘要页标题：16 pt 宋体加粗。
  % 不使用 center 环境，避免自动加入额外上下留白。
  \vspace*{-26.1pt}%
  {%
    \centering
    \songti\bfseries\fontsize{16pt}{19.2pt}\selectfont
    \@title\par
  }%
}

% ============================================================
% 摘要
% ============================================================
\renewenvironment{abstract}{%
  % “摘要”：14 pt 宋体加粗。
  \vspace{8pt}%
  {%
    \centering
    \songti\bfseries\fontsize{14pt}{16.8pt}\selectfont
    摘要\par
  }%

  % 摘要正文直接使用 25 mm 版心，不再额外左右缩进。
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

# LF_HF_COMPATIBILITY_MATRIX

HF为integrated 3D periodic plane-wave：GaN+固定MDC+237 nm SiO2+ordered K6+air，440–460 nm、P/XLIKE。输出为POSTNP +z，m=-3…3、n=0，TE/TM复数坐标，reference=1722 nm；保留incident gauge。独立预测P_scale，原H2进行physical reconstruction。单入射state不是完整多端口operator。

| 对齐项 | NP | MDC | 结论 |
|---|---|---|---|
| ordered/origin | D1…D6保持位置；DFT用内部j顺序 | 固定平面层 | 几何grammar兼容，DFT相位不等于已验证物理phase origin |
| wavelength | 445–455 | 440–460 | 只有11点共有域，无NP全波段baseline |
| diffraction orders | 透射7，SiO2反射11 | 冻结normal m=0 | 缺返回m≠0及必要closed/evanescent通道 |
| polarization | P/S入射分支、投影阶state | normal TE/TM degenerate | 需明确basis转换；缺完整返回通道TE/TM mixing operator |
| ports | 候选0-/500+，raw -300/900 nm | GaN0 / SiO2 975 | NP bottom映射1212=975+237明确，但只解决几何位置 |
| reference/phase | raw monitor phase，无incident complex division | interface gauge | FAIL：不能映射为共同incident gauge |
| normalization | sqrt(power)×gratingvector | E-field amplitude+admittance | FAIL：不是同构C_PW单位 |
| reflection loop | 仅normal m=0入射 | normal双向 | 无法闭合完整multiple scattering |
| factorization | proxy fraction不提供integrated scale | cavity prior不提供integrated truth | 禁止oracle P_scale、功率级联伪truth |
| H2/H1 | 只能作为辅助输入 | 只能作为合法解析conditioning | 原HF输出和gates保持不变 |

若b为NP substrate port入射，a为外部入射，P为spacer传播，R_M为MDC spacer侧反射，R_N为NP substrate侧反射，T_M为MDC注入，T_N为NP出射，合法的多次反射基线形式为：

b = (I - P R_M P R_N)^(-1) P T_M a
C_LF = Q_out T_N b

Q_out必须完成到1722 nm的传播及与C_PW相同的入射复数归一化。矩阵需覆盖order、TE/TM及必要倏逝通道。平面MDC守恒kx、分离TE/TM；NP可混阶/矢量分量。不能用scalar efficiency乘积代替该方程。

本轮不构造任何C_LF数值。即便single-pass，也必须先有合法NP incident-normalized coefficients。仅m=0反馈近似需声明假设和验证，不是精确integrated coupling。raw E/H standing field不自动等于隔离的反射算子；正式NP合同判定入射相位不可恢复，重新开启需新证据/authority。
